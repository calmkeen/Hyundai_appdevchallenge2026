"""Pure grounding checks over guides already accepted by Catalog publication policy.

An answer selects one complete reviewed passage. Step cautions travel with the
step, and citations belong to that passage rather than any text in its guide.
This does not certify publication metadata, vehicle identity, or translation.
"""


def answer_units(guides):
    units = []
    for guide in guides:
        identity = ":".join((guide["guide_id"], guide["locale"], guide["source_version"]))
        units.append({
            "unit_id": identity + ":body", "guide_id": guide["guide_id"],
            "text": guide["body"],
            "source_ids": [source["source_id"] for source in guide["sources"]],
        })
        for step in guide["steps"]:
            units.append({
                "unit_id": identity + ":step:" + step["step_id"],
                "guide_id": guide["guide_id"],
                "text": "\n".join([step["body"], *step["official_cautions"]]),
                "source_ids": list(step["source_ids"]),
            })
    return units


def validate_answer(output, guides):
    """Return one exactly grounded ANSWERED unit or raise a stable ValueError.

    The API layer separately replaces other model statuses with localized server
    text. No whitespace trimming or substring match may drop a caution/negation.
    """
    def field(name):
        return output.get(name) if isinstance(output, dict) else getattr(output, name, None)

    if field("status") != "ANSWERED":
        raise ValueError("ANSWER_STATUS_REQUIRED")
    text, citations = field("answer"), field("source_ids")
    if not isinstance(text, str) or not text:
        raise ValueError("EMPTY_GROUNDED_ANSWER")
    if (not isinstance(citations, list) or not citations
            or any(not isinstance(source_id, str) or not source_id for source_id in citations)
            or len(citations) != len(set(citations))):
        raise ValueError("INVALID_ANSWER_CITATIONS")
    matches = [unit for unit in answer_units(guides)
               if text == unit["text"] and set(citations) == set(unit["source_ids"])]
    if not matches:
        raise ValueError("ANSWER_NOT_GROUNDED_IN_COMPLETE_UNIT")
    if len(matches) != 1:
        raise ValueError("AMBIGUOUS_ANSWER_UNIT")
    return matches[0]
