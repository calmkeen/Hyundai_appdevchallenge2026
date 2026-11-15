import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from .guide_policy import ValidationIssue, validate_guide
from .official_links import registered_support_contacts, resolve_support, resolve_manual

ROOT = Path(__file__).resolve().parents[2]

# Search aliases identify the reviewed door topic, not additional procedures.
# Korean particles and Japanese sentences cannot be split on spaces like English.
_DOOR_QUERY = re.compile(
    r"\bdoors?\b|ドア|扉|도어|"
    r"(?<![가-힣a-z])문(?=$|[\s?!.,:·]|이|을|은|에|과|도|만|부터|까지|열|닫|틈)",
    re.IGNORECASE,
)
_CHARGING_QUERY = re.compile(r"\bcharg(?:e|es|ed|ing|er|ers)\b|충전|充電|チャージ", re.IGNORECASE)
_TOPIC_QUERIES = {
    "door": _DOOR_QUERY,
    "charging": _CHARGING_QUERY,
    "seats_mirrors": re.compile(r"\b(?:seats?|mirrors?)\b|좌석|시트|거울|미러|シート|座席|ミラー|鏡", re.IGNORECASE),
    "display_indicators": re.compile(r"(?<![a-z0-9])(?:cluster|dashboard|display|indicators?|telltales?|ready)(?![a-z0-9])|power[ -]?down|"
        r"계기판|클러스터|표시등|경고등|밝기|화면|출력\s*제한|パワーダウン|メーター|表示灯|警告灯|明るさ|画面|ディスプレイ", re.IGNORECASE),
}
_CHARGE_PORT_DOOR = re.compile(r"charg\w*\s+port\s+door|충전\s*(?:구\s*(?:도어|문)|도어)|充電(?:口|ポート)(?:の)?(?:ドア|扉)", re.IGNORECASE)
_OUTSIDE_TOPIC_SCOPE = {
    "charging": re.compile(r"(?<![a-z0-9])(?:dc|iccb|v2l|chademo|ccs)(?![a-z0-9])|\b(?:fast|rapid|portable|emergency)\b|"
        r"(?<![a-z0-9])(?:phones?|smartphones?|usb|wireless|12\s*v)(?![a-z0-9])|"
        r"급속|휴대용|휴대폰|휴대전화|스마트폰|무선|비상\s*(?:분리|해제)|강제\s*분리|"
        r"急速|携帯|スマホ|スマートフォン|ワイヤレス|無線|ポータブル|非常|緊急", re.IGNORECASE),
    "seats_mirrors": re.compile(r"(?<![a-z0-9])(?:dsm|memory|relaxation|reverse|camera)(?![a-z0-9])|seat[ -]?belts?|"
        r"rear\s+seats?|child\s+seats?|메모리|릴렉|카메라|후진|디지털|안전벨트|뒷좌석|카시트|유아|"
        r"デジタル|カメラ|メモリ|リラック|後退|バック|後席|チャイルド|シートベルト", re.IGNORECASE),
    "display_indicators": re.compile(r"(?<![a-z0-9])(?:abs|tpms|brake|airbag|esc)(?![a-z0-9])|브레이크|제동|타이어|공기압|에어백|"
        r"ブレーキ|タイヤ|空気圧|エアバッグ", re.IGNORECASE),
}
# Full-match only: a selected door guide may resolve a short referential
# follow-up, never supply sources for an arbitrary different question.
_DOOR_FOLLOWUP = re.compile(
    r"(?:(?:그\s*)?다음(?:에는|엔|은)?요|(?:그\s*)?다음\s*단계는(?:\s*무엇인가요)?|"
    r"what(?:'s| is)?\s+next|what should i do next|what is the next step|next step|"
    r"(?:その)?次は|次(?:はどう|に何を)すればいいですか|次の手順は)[\s?!。.!]*",
    re.IGNORECASE,
)


def _door_guide(guide):
    # The publication contract also supports a body-only guide. With steps,
    # require an explicit property association instead of guessing from its text.
    return guide["topic"] == "door" and (not guide["steps"] or any(
        "door.position" in step["related_properties"] for step in guide["steps"]))


class Catalog:
    def __init__(self, root: Path = ROOT / "content"):
        self.profiles = json.loads((root / "profiles/catalog.json").read_text())
        self.locales = json.loads((root / "locales/catalog.json").read_text())
        self.guides = [json.loads(path.read_text()) for path in sorted((root / "guides").glob("*.json"))]
        self.publication_issues = {}
        self._publication_candidates()

    def profile(self, profile_id):
        return next((p for p in self.profiles if p["profile_id"] == profile_id), None)

    def locale(self, locale):
        return next((item for item in self.locales if item["locale"] == locale), None)

    def support_contacts(self, profile_id):
        matches = [profile for profile in self.profiles if profile.get("profile_id") == profile_id]
        return registered_support_contacts(matches[0], self.locales) if len(matches) == 1 else []

    def support(self, profile_id, target_id):
        matches = [profile for profile in self.profiles if profile.get("profile_id") == profile_id]
        return resolve_support(matches[0], self.locales, target_id) if len(matches) == 1 else None

    def manual_source(self, profile_id, locale, target_id):
        return resolve_manual(self.published(profile_id, locale), self.profile(profile_id), target_id)

    def public_profile(self, profile):
        # Do not expose an invalid support record merely because its profile exists.
        return {**profile, "support_contacts": self.support_contacts(profile["profile_id"])}

    def published(self, profile_id, locale=None):
        candidates = self._publication_candidates()
        p = self.profile(profile_id)
        if not p or p["verification_status"] != "VERIFIED":
            return []
        return [g for g in candidates if profile_id in g["profile_ids"]
                and (locale is None or g["locale"] == locale)]

    def _publication_candidates(self):
        # Revalidate on reads so a reload or in-memory catalog update cannot keep
        # serving content whose profile, review metadata, or record has changed.
        self.publication_issues = {}
        fields = ("guide_id", "locale", "manual_set_id", "source_version")

        def identity(guide):
            if (isinstance(guide, dict) and guide.get("lifecycle") == "PUBLISHED"
                    and all(isinstance(guide.get(field), str) for field in fields)):
                return tuple(guide[field] for field in fields)
            return None

        # Translations and manual-version variants share guide_id by design.
        # Only collisions of the full immutable record identity are ambiguous.
        # An invalid colliding record must not make an otherwise ambiguous ID
        # appear unique merely because that record failed its own policy check.
        identities = Counter(key for guide in self.guides if (key := identity(guide)) is not None)
        result = []
        for index, guide in enumerate(self.guides):
            issues = validate_guide(guide, self.profiles, self.locales)
            if identities[identity(guide)] > 1:
                issues.append(ValidationIssue(
                    "DUPLICATE_GUIDE_RECORD", "", "Guide ID, locale, manual set and version identify more than one published record."))
            if issues:
                self.publication_issues[index] = issues
            elif guide["lifecycle"] == "PUBLISHED":
                result.append(guide)
        return result

    def search(self, profile_id, locale, query="", topic=None):
        # Do not silently use a different language, vehicle, market or manual version.
        guides = self.published(profile_id, locale)
        if topic:
            guides = [g for g in guides if g["topic"] == topic]
        terms = query.casefold().split()[:12]
        if not terms:
            return guides[:5]
        scored = [(sum(t in (g["title"] + " " + g["body"]).casefold() for t in terms), g) for g in guides]
        return [g for score, g in sorted(scored, key=lambda pair: pair[0], reverse=True) if score][:5]

    def retrieve(self, request):
        guides = self.published(request.profile_id, request.locale)
        query = unicodedata.normalize("NFKC", request.question).casefold()
        topics = {topic for topic, pattern in _TOPIC_QUERIES.items() if pattern.search(query)}
        if "charging" in topics and _CHARGE_PORT_DOOR.search(query):
            topics.discard("door")
        # One complete reviewed topic cannot answer a compound cross-topic question.
        if len(topics) > 1:
            return []
        selected_topic = next(iter(topics), None)
        if selected_topic in _OUTSIDE_TOPIC_SCOPE and _OUTSIDE_TOPIC_SCOPE[selected_topic].search(query):
            return []
        if selected_topic:
            matches = [g for g in guides if g["topic"] == selected_topic
                       and (selected_topic != "door" or _door_guide(g))]
        else:
            # Preserve legacy search for other topics. These four published
            # scopes require an explicit topic or a short contextual follow-up.
            matches = [g for g in self.search(request.profile_id, request.locale, request.question)
                       if g["topic"] not in _TOPIC_QUERIES]
        if request.guide_context.guide_id:
            context = next((g for g in guides if g["guide_id"] == request.guide_context.guide_id
                            and (g["topic"] != "door" or _door_guide(g))
                            and ((selected_topic is not None and g["topic"] == selected_topic)
                                 or (selected_topic is None and _DOOR_FOLLOWUP.fullmatch(query.strip())))), None)
            if context and context not in matches:
                matches.insert(0, context)
        return matches[:5]
