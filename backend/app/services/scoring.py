"""
Epic 2 — AI risk engine (Layer 2, our build, differentiator 1).

Owner: whoever is assigned Epic 2 in OWNERSHIP.md.
You read from the dict that parsing.py produces (see PARSED_SHAPE in
services/parsing.py) - don't reach into app/lib/eml_parser directly.

CONTRACT:
    score_email(parsed: dict) -> dict
        Returns a dict shaped like SCORE_SHAPE below.
        Rule: AI-generated content must never lower the score below the
        rule-based floor (master doc, section 5, backend security rules) -
        combine_scores() below is where you enforce that, keep it that way
        even if you rewrite the rest.
"""

SCORE_SHAPE = {
    "riskScore": 0,             # int, 0-100
    "severity": "green",        # "green" | "yellow" | "red"
    "urgencyLanguage": "low",   # "low" | "medium" | "high"
    "impersonationScore": 0.0,  # float, 0-1
    "summary": "",              # one-line plain-English reasoning
}


def rule_based_score(parsed: dict) -> int:
    # TODO (Epic 2, step 1): missing SPF/DKIM adds points, sender/domain
    # mismatch adds points. This should work on Day 1 with no AI call.
    score = 0
    if parsed.get("spf") == "fail":
        score += 25
    if parsed.get("dkim") == "fail":
        score += 25
    if parsed.get("from_domain") and parsed.get("reply_to_domain"):
        if parsed["from_domain"] != parsed["reply_to_domain"]:
            score += 20
    return min(score, 100)


def ai_score(parsed: dict) -> dict:
    # TODO (Epic 2, step 2): send parsed["body_text"] / parsed["subject"] to
    # an LLM, ask it to rate urgency, manipulation language, impersonation.
    # Return {"points": int, "urgencyLanguage": ..., "impersonationScore": ..., "summary": ...}
    return {
        "points": 0,
        "urgencyLanguage": "low",
        "impersonationScore": 0.0,
        "summary": "AI scoring not yet implemented.",
    }


def combine_scores(rule_points: int, ai_result: dict) -> dict:
    # Floor rule: never let the AI layer pull the score below what rules alone found.
    combined = max(rule_points, min(rule_points + ai_result["points"], 100))
    severity = "green" if combined < 40 else "yellow" if combined < 70 else "red"
    return {
        "riskScore": combined,
        "severity": severity,
        "urgencyLanguage": ai_result["urgencyLanguage"],
        "impersonationScore": ai_result["impersonationScore"],
        "summary": ai_result["summary"],
    }


def score_email(parsed: dict) -> dict:
    rule_points = rule_based_score(parsed)
    ai_result = ai_score(parsed)
    return combine_scores(rule_points, ai_result)
