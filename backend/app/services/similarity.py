"""
Epic 3 — Case memory (Layer 3, our build, differentiator 2 - the core idea).

Owner: whoever is assigned Epic 3 in OWNERSHIP.md.
Paired with geolocation.py, which you also own.

CONTRACT:
    find_related_cases(parsed: dict, origin: dict, case_store: list[dict]) -> list[dict]
        `case_store` is every previously analysed case (from wherever cases
        are persisted - coordinate with the Epic 4 owner on the storage
        shape). Returns a list shaped like RELATED_CASE_SHAPE, sorted by
        similarity descending, only including matches above the 0.6 threshold.
"""

RELATED_CASE_SHAPE = {
    "caseId": "",
    "similarity": 0.0,       # 0-1, combined score
    "matchedOn": [],         # e.g. ["domain", "ip_block", "content"]
}

SIMILARITY_THRESHOLD = 0.6


def domain_similarity(domain_a: str | None, domain_b: str | None) -> float:
    # TODO (Epic 3): exact match = 1.0, close spelling match (e.g. paypa1.com
    # vs paypal.com) = partial credit, otherwise 0.
    if domain_a and domain_b and domain_a == domain_b:
        return 1.0
    return 0.0


def ip_similarity(ip_a: str | None, ip_b: str | None) -> float:
    # TODO (Epic 3): same /24 block or same ASN = high score.
    return 0.0


def content_similarity(text_a: str, text_b: str) -> float:
    # TODO (Epic 3): TF-IDF + cosine similarity between email bodies.
    return 0.0


def find_related_cases(parsed: dict, origin: dict, case_store: list[dict]) -> list[dict]:
    results = []
    for prior in case_store:
        combined = (
            0.4 * domain_similarity(parsed.get("from_domain"), prior.get("from_domain"))
            + 0.3 * ip_similarity(origin.get("ip"), prior.get("origin_ip"))
            + 0.3 * content_similarity(parsed.get("body_text", ""), prior.get("body_text", ""))
        )
        if combined >= SIMILARITY_THRESHOLD:
            results.append({
                "caseId": prior["caseId"],
                "similarity": round(combined, 2),
                "matchedOn": [],  # TODO: list which signals actually matched
            })
    return sorted(results, key=lambda r: r["similarity"], reverse=True)
