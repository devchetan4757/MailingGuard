# dispatcher.py
#
# Maps a UI-selected "deep analysis" option to the right analyzer
# function and runs it. Called AFTER the user has already picked
# what to analyze (link / domain / attachment) -- no AI decision
# making happens here, it's a plain dispatch table.
#
# pdf_analyzer and image_analyzer run in a subprocess with a
# timeout, since they parse untrusted, possibly malicious files.
# crawler and whois run in-process since they're low-risk / text-only.

import json
import subprocess
import sys
from pathlib import Path

from app.ai_analyzers.crawler.crawler import crawl
from app.ai_analyzers.whois.whois_lookup import lookup_domain

# Paths to the CLI-wrapped scripts (used for subprocess isolation)
BASE_DIR = Path(__file__).resolve().parent
PDF_ANALYZER_SCRIPT = BASE_DIR / "ai_analyzers" / "pdf_analyzer" / "analyzer_cli.py"
# NOTE: the folder on disk is "image-analyzer" (hyphen), not "image_analyzer"
# (underscore). This previously pointed at a path that never existed, so
# every "Scan image attachment" request silently failed with
# "Analyzer produced no output."
IMAGE_ANALYZER_SCRIPT = BASE_DIR / "ai_analyzers" / "image-analyzer" / "deep_image_analyzer.py"

SUBPROCESS_TIMEOUT_SECONDS = 30


def _run_isolated(script_path, arg):
    """Run a script in a subprocess, parse its JSON stdout, enforce a timeout."""

    try:
        result = subprocess.run(
            [sys.executable, str(script_path), arg],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Analysis timed out after {SUBPROCESS_TIMEOUT_SECONDS}s"}

    if not result.stdout.strip():
        return {"error": result.stderr.strip() or "Analyzer produced no output."}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "Could not parse analyzer output.", "raw": result.stdout[:2000]}


def analyze_link(url: str) -> dict:
    """UI option: 'Analyze links found in this email'."""
    try:
        return crawl(url)
    except Exception as error:
        return {"error": str(error), "url": url}


def analyze_sender_domain(domain: str) -> dict:
    """UI option: 'Check sender domain'."""
    return lookup_domain(domain)


def analyze_pdf_attachment(file_path: str) -> dict:
    """UI option: 'Scan PDF attachment'. Runs isolated in a subprocess."""
    return _run_isolated(PDF_ANALYZER_SCRIPT, file_path)


def analyze_image_attachment(file_path: str) -> dict:
    """UI option: 'Scan image attachment'. Runs isolated in a subprocess."""
    return _run_isolated(IMAGE_ANALYZER_SCRIPT, file_path)


# Single entry point your route/controller can call with the UI option id
DISPATCH_TABLE = {
    "analyze_link": analyze_link,
    "analyze_sender_domain": analyze_sender_domain,
    "analyze_pdf_attachment": analyze_pdf_attachment,
    "analyze_image_attachment": analyze_image_attachment,
}


def run_deep_analysis(option_id: str, payload: str) -> dict:
    """
    option_id: one of DISPATCH_TABLE's keys (comes from the UI button clicked)
    payload:   the url / domain / file path relevant to that option
    """

    handler = DISPATCH_TABLE.get(option_id)

    if handler is None:
        return {"error": f"Unknown analysis option: {option_id}"}

    return handler(payload)
