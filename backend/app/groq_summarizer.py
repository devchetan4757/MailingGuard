# groq_summarizer.py
#
# Takes the raw dict from an analyzer (crawler / whois / pdf / image)
# and asks Groq to turn it into a short, plain-language explanation
# for the end user. No tool-calling needed here -- the analyzer has
# already run deterministically; Groq's only job is to narrate the
# result.
#
# Requires: pip install groq
# Requires: GROQ_API_KEY set in the environment

import json

from groq import Groq

from app.core.config import settings

# Keep this fast/cheap since it's just narrating structured JSON,
# not doing complex reasoning. Swap for a larger Groq model if you
# want deeper judgement calls.
MODEL = settings.GROQ_MODEL

# Built lazily (not at import time) so the whole backend doesn't fail to
# start just because GROQ_API_KEY isn't set yet -- deep-analysis routes
# degrade to "raw result, no explanation" instead in that case
# (see app/api/deep_analysis.py).
_client: "Groq | None" = None


def _get_client() -> Groq:
    global _client

    if _client is None:
        if not settings.GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to backend/.env to enable "
                "AI-written explanations for deep analysis results."
            )

        _client = Groq(api_key=settings.GROQ_API_KEY)

    return _client

SYSTEM_PROMPTS = {
    "analyze_link": (
        "You explain website crawl results to a non-technical user checking "
        "if a link from an email is safe. Mention the page title, whether "
        "links look internal/external, and anything that looks suspicious "
        "(e.g. mismatched domains, no title, excessive external links). "
        "Give a short verdict: Looks safe / Be cautious / Looks suspicious."
    ),
    "analyze_sender_domain": (
        "You explain WHOIS/DNS results to a non-technical user checking if "
        "an email sender's domain looks legitimate. Highlight domain age "
        "(very new domains are a red flag), registrar, and any warnings. "
        "Give a short verdict: Looks legitimate / Be cautious / Looks suspicious."
    ),
    "analyze_pdf_attachment": (
        "You explain a PDF security scan to a non-technical user. Summarize "
        "the risk level, any risky phrases found (credential requests, "
        "urgency, financial requests), suspicious PDF features (JavaScript, "
        "embedded files, auto-actions), and URLs found. Give a short verdict "
        "matching the tool's risk status."
    ),
    "analyze_image_attachment": (
        "You explain an image metadata/forensic scan to a non-technical "
        "user. Highlight any privacy findings (GPS location, device serial "
        "numbers, editing software) and flag anything unusual. Give a short "
        "verdict: No concerns / Minor privacy exposure / Notable concerns."
    ),
}


def summarize_analysis(option_id: str, result: dict) -> str:
    """
    option_id: same key used in dispatcher.DISPATCH_TABLE
    result:    the raw dict returned by that analyzer
    """

    system_prompt = SYSTEM_PROMPTS.get(
        option_id,
        "You explain a security analysis result to a non-technical user "
        "in 3-5 sentences, ending with a short verdict."
    )

    if result.get("error"):
        return f"The analysis couldn't be completed: {result['error']}"

    response = _get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "Here is the raw analysis result as JSON. Summarize it "
                    "for the user in plain language, 3-6 sentences, ending "
                    "with a one-line verdict.\n\n"
                    f"{json.dumps(result, default=str)[:6000]}"
                )
            }
        ],
        temperature=0.3,
        max_tokens=400
    )

    return response.choices[0].message.content


# ============================================================
# Convenience: run dispatch + summarize in one call
# ============================================================

def analyze_and_explain(option_id: str, payload: str) -> dict:
    from app.dispatcher import run_deep_analysis

    raw_result = run_deep_analysis(option_id, payload)
    explanation = summarize_analysis(option_id, raw_result)

    return {
        "option": option_id,
        "raw_result": raw_result,
        "explanation": explanation
    }
