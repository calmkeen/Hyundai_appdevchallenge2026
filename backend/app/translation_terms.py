"""Versioned question vocabulary, not a full translation-meaning validator.

Reviewed phrases must occur in the exact scoped published guide. Lookup and
target checks are pure and never replace text, call a model or promote review.
"""
import copy
import json
import re
import unicodedata
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "content/glossary/assistant-question-v1.json"


def normalized(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def contains_term(text, phrase):
    phrase = normalized(phrase)
    left = r"(?<![a-z0-9_])" if phrase[0].isascii() and phrase[0].isalnum() else ""
    right = r"(?![a-z0-9_])" if phrase[-1].isascii() and phrase[-1].isalnum() else ""
    return re.search(left + re.escape(phrase) + right, normalized(text)) is not None


def _require(condition, code):
    if not condition:
        raise ValueError(code)


class QuestionTerms:
    @classmethod
    def from_data(cls, data, catalog):
        return cls(data, catalog)

    def __init__(self, data, catalog):
        _require(isinstance(data, dict) and data.get("status") == "REVIEWED"
                 and data.get("content_kind") == "QUESTION", "QUESTION_TERMS_NOT_REVIEWED")
        _require(isinstance(data.get("version"), str) and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", data["version"]), "QUESTION_TERMS_VERSION_INVALID")
        _require(data.get("human_certified_review") is False and data.get("oem_approved") is False
                 and isinstance(data.get("review_method"), str) and bool(data["review_method"].strip()), "QUESTION_TERMS_REVIEW_METADATA_INVALID")
        scope = data.get("scope", {})
        fields = ("profile_id", "manual_set_id", "source_version", "guide_id")
        _require(isinstance(scope, dict) and all(isinstance(scope.get(key), str) and scope[key].strip() for key in fields), "QUESTION_TERMS_SCOPE_INVALID")
        profile = catalog.profile(scope["profile_id"])
        _require(profile is not None and profile.get("verification_status") == "VERIFIED"
                 and profile.get("manual_set_id") == scope["manual_set_id"]
                 and profile.get("manual_version") == scope["source_version"], "QUESTION_TERMS_PROFILE_OR_MANUAL_UNREGISTERED")
        terms = data.get("terms")
        _require(isinstance(terms, list) and bool(terms), "QUESTION_TERMS_EMPTY")
        identifiers = set()
        for term in terms:
            _require(isinstance(term, dict) and term.get("review_status") == "REVIEWED", "QUESTION_TERM_NOT_REVIEWED")
            term_id = term.get("term_id")
            _require(isinstance(term_id, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", term_id)
                     and term_id not in identifiers, "QUESTION_TERM_ID_INVALID")
            identifiers.add(term_id)
            phrases = term.get("phrases")
            _require(isinstance(phrases, dict) and len(phrases) >= 2, "QUESTION_TERM_PHRASES_INVALID")
            for locale, phrase in phrases.items():
                language = catalog.locale(locale)
                _require(language is not None and language.get("ui_status", "PLANNED") != "PLANNED", "QUESTION_TERM_LOCALE_UNREGISTERED")
                _require(isinstance(phrase, str) and bool(phrase.strip()), "QUESTION_TERM_PHRASE_INVALID")
                guides = [guide for guide in catalog.published(scope["profile_id"], locale)
                          if guide["guide_id"] == scope["guide_id"] and guide["manual_set_id"] == scope["manual_set_id"]
                          and guide["source_version"] == scope["source_version"]]
                _require(len(guides) == 1 and phrase in guides[0]["body"], "QUESTION_TERM_NOT_IN_REVIEWED_BODY")
        self._data = copy.deepcopy(data)

    def lookup(self, profile, source_locale, target_locale, text):
        scope = self._data["scope"]
        if (not isinstance(profile, dict) or profile.get("verification_status") != "VERIFIED"
                or profile.get("profile_id") != scope["profile_id"] or profile.get("manual_set_id") != scope["manual_set_id"]
                or profile.get("manual_version") != scope["source_version"] or not isinstance(text, str)):
            return None
        matches = []
        for term in self._data["terms"]:
            phrases = term["phrases"]
            if target_locale not in phrases:
                continue
            sources = phrases if source_locale == "auto" else [source_locale]
            for source in sources:
                if source in phrases and contains_term(text, phrases[source]):
                    matches.append({"term_id": term["term_id"], "source_locale": source, "target_locale": target_locale,
                                    "source": phrases[source], "target": phrases[target_locale]})
        return {"version": self._data["version"], "terms": matches} if matches else None


def load_question_terms(path=DEFAULT_PATH, catalog=None):
    if catalog is None:
        from .content import Catalog
        catalog = Catalog()
    return QuestionTerms.from_data(json.loads(Path(path).read_text()), catalog)


def validate_target_terms(match, translated_text):
    if match is None:
        return None
    _require(all(contains_term(translated_text, term["target"]) for term in match["terms"]), "TRANSLATION_REQUIRED_TERM_MISSING")
    return match["version"]
