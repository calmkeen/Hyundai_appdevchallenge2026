import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


class Catalog:
    def __init__(self, root: Path = ROOT / "content"):
        self.profiles = json.loads((root / "profiles/catalog.json").read_text())
        self.locales = json.loads((root / "locales/catalog.json").read_text())
        self.guides = [json.loads(path.read_text()) for path in (root / "guides").glob("*.json")]
        validator = Draft202012Validator(json.loads((ROOT / "contracts/guide.schema.json").read_text()))
        for guide in self.guides:
            validator.validate(guide)

    def profile(self, profile_id):
        return next((p for p in self.profiles if p["profile_id"] == profile_id), None)

    def locale(self, locale):
        return next((item for item in self.locales if item["locale"] == locale), None)

    def published(self, profile_id, locale=None):
        p = self.profile(profile_id)
        if not p or p["verification_status"] != "VERIFIED":
            return []
        return [g for g in self.guides if profile_id in g["profile_ids"]
                and g["lifecycle"] == "PUBLISHED"
                and g["manual_set_id"] == p["manual_set_id"]
                and g["source_version"] == p["manual_version"]
                and (locale is None or g["locale"] == locale)
                and g["translation_review_status"] in ("REVIEWED", "NOT_APPLICABLE")
                and (g["locale"] == g["source_locale"] or g["translation_review_status"] == "REVIEWED")
                and g["sources"] and all(s["verification_status"] == "VERIFIED"
                    and s.get("section") and s.get("version") == g["source_version"]
                    and s["url"].startswith("https://") for s in g["sources"])]

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
        matches = self.search(request.profile_id, request.locale, request.question)
        if request.guide_context.guide_id:
            context = next((g for g in self.published(request.profile_id, request.locale)
                            if g["guide_id"] == request.guide_context.guide_id), None)
            if context and context not in matches:
                matches.insert(0, context)
        return matches[:5]
