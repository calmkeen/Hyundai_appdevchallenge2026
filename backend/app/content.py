import json
from collections import Counter
from pathlib import Path

from .guide_policy import ValidationIssue, validate_guide

ROOT = Path(__file__).resolve().parents[2]


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
        matches = self.search(request.profile_id, request.locale, request.question)
        if request.guide_context.guide_id:
            context = next((g for g in self.published(request.profile_id, request.locale)
                            if g["guide_id"] == request.guide_context.guide_id), None)
            if context and context not in matches:
                matches.insert(0, context)
        return matches[:5]
