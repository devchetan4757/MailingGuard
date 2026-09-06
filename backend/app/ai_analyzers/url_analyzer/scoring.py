# scoring.py
#
# Turns the raw output of every analyzer into one risk_score (0-100),
# a risk_level, and a plain-language list of "flags" explaining why.
# Any source that errored or was skipped (missing API key) is simply
# left out of the score rather than penalized -- an unavailable check
# should never look like a clean bill of health OR a red flag.

def _points(condition, amount, flags, label):
    if condition:
        flags.append(label)
        return amount
    return 0


def score(results: dict) -> dict:
    score_total = 0
    flags = []

    sb = results.get("safe_browsing", {})
    score_total += _points(
        sb.get("malicious"), 30, flags,
        f"Google Safe Browsing: flagged as {', '.join(sb.get('threat_types', [])) or 'malicious'}"
    )

    op = results.get("openphish", {})
    score_total += _points(op.get("listed"), 20, flags, "OpenPhish: listed in active phishing feed")

    uh = results.get("urlhaus", {})
    score_total += _points(
        uh.get("listed"), 25, flags,
        f"URLhaus: distributing malware ({uh.get('threat', 'unknown')})"
    )

    us = results.get("urlscan", {})
    if us.get("malicious"):
        score_total += 20
        flags.append(f"urlscan.io: sandbox verdict malicious (score {us.get('score')})")

    vt = results.get("virustotal", {})
    malicious_count = vt.get("malicious_count", 0) or 0
    suspicious_count = vt.get("suspicious_count", 0) or 0
    if malicious_count:
        pts = min(malicious_count * 5, 30)
        score_total += pts
        flags.append(f"VirusTotal: {malicious_count} engines flagged malicious")
    if suspicious_count:
        pts = min(suspicious_count * 2, 10)
        score_total += pts
        flags.append(f"VirusTotal: {suspicious_count} engines flagged suspicious")

    whois_warnings = results.get("whois", {}).get("warnings", [])
    for warning in whois_warnings:
        if "less than 30 days" in warning:
            score_total += 15
            flags.append(f"WHOIS: {warning}")
        elif "less than 6 months" in warning:
            score_total += 5
            flags.append(f"WHOIS: {warning}")

    dt = results.get("dnstwist", {})
    lookalike_count = dt.get("registered_lookalike_count", 0) or 0
    # Was gated behind >= 5, which real typosquat campaigns rarely reach --
    # most show up as 1-4 registered lookalikes, so this basically never
    # fired and dnstwist never affected the verdict no matter what it found.
    if lookalike_count >= 10:
        score_total += 15
        flags.append(f"dnstwist: {lookalike_count} registered lookalike domains found (likely campaign infrastructure)")
    elif lookalike_count >= 5:
        score_total += 10
        flags.append(f"dnstwist: {lookalike_count} registered lookalike domains found (possible campaign infrastructure)")
    elif lookalike_count >= 1:
        score_total += 5
        flags.append(f"dnstwist: {lookalike_count} registered lookalike domain{'s' if lookalike_count != 1 else ''} found")

    aid = results.get("abuseipdb", {})
    confidence = aid.get("abuse_confidence_score")
    if isinstance(confidence, (int, float)) and confidence > 0:
        pts = min(round(confidence / 100 * 20), 20)
        score_total += pts
        flags.append(f"AbuseIPDB: {confidence}% abuse confidence on hosting IP")

    sh = results.get("shodan", {})
    if sh.get("vulnerabilities"):
        score_total += 10
        flags.append(f"Shodan: known vulnerabilities on hosting IP ({len(sh['vulnerabilities'])})")

    score_total = min(score_total, 100)

    if score_total >= 75:
        level = "critical"
    elif score_total >= 50:
        level = "high"
    elif score_total >= 20:
        level = "medium"
    else:
        level = "low"

    return {
        "risk_score": score_total,
        "risk_level": level,
        "flags": flags,
    }
