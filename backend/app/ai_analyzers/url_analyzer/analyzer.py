# analyzer.py
#
# Runs every analyzer in this package at the same time (one thread
# each) and merges everything into a single result with a combined
# risk verdict. Total time is roughly the slowest single source
# (usually urlscan.io, ~15-25s) rather than the sum of all of them.
#
# Sources, and whether they need a free API key (see config.py):
#   crawler          -- no key   -- fetches + parses the page itself
#   whois_lookup     -- no key   -- WHOIS + DNS records
#   safe_browsing    -- KEY      -- Google Safe Browsing v4
#   openphish        -- no key   -- active phishing feed
#   urlhaus          -- KEY      -- malware-distribution URLs
#   urlscan          -- KEY      -- sandboxed browser detonation
#   virustotal       -- KEY      -- 70+ engine aggregate verdict
#   crt_sh           -- no key   -- certificate transparency logs
#   dnstwist         -- no key   -- typosquat/lookalike domains
#   abuseipdb        -- KEY      -- hosting IP abuse reports
#   shodan           -- KEY      -- hosting IP open ports/vulns
#
# Usage:
#   from analyzer import analyze_url
#   result = analyze_url("https://example.com/some/path")

import sys
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError, as_completed
from urllib.parse import urlparse

import tldextract

try:
    from . import crawler, whois_lookup, safe_browsing, openphish
    from . import urlhaus, urlscan_check, virustotal, crtsh, dnstwist_check
    from . import abuseipdb, shodan_check, scoring
except ImportError:
    import crawler, whois_lookup, safe_browsing, openphish
    import urlhaus, urlscan_check, virustotal, crtsh, dnstwist_check
    import abuseipdb, shodan_check, scoring

# Per-source timeout. urlscan/virustotal poll internally and can take
# up to ~25s themselves; everything else should be fast. This is the
# ceiling we wait before giving up on any ONE source -- a slow source
# never blocks the others or the overall result.
SOURCE_TIMEOUT_SECONDS = 65


def _extract_domain(url: str) -> str:
    candidate = url.strip()
    if "://" not in candidate:
        candidate = "http://" + candidate
    parsed = urlparse(candidate)
    return parsed.netloc or url


def _registrable_domain(hostname: str) -> str:
    """
    Reduce a possibly-long subdomain (e.g. a tracking-pixel host like
    s-2iz520k...xyz.sendgrid.net) down to its real registrable domain
    (sendgrid.net) -- dnstwist and crt.sh should check typosquats/certs
    against the actual owning domain, not a random one-off subdomain
    string, which was causing dnstwist to blow up its permutation set
    (timeouts) and crt.sh to query an obscure string unlikely to ever
    have its own certificate.
    """
    extracted = tldextract.extract(hostname)
    if not extracted.domain or not extracted.suffix:
        return hostname
    return f"{extracted.domain}.{extracted.suffix}"


def _safe(fn, *args):
    """Wrap a source call so an unexpected exception becomes an error dict, never a crash."""
    try:
        return fn(*args)
    except Exception as error:
        return {"source": getattr(fn, "__module__", "unknown"), "error": str(error)}


def analyze_url(url: str) -> dict:
    domain = _extract_domain(url)
    registrable_domain = _registrable_domain(domain)

    # (result_key, function, args) -- submitted together, gathered together
    jobs = {
        "crawl": (lambda: _safe(crawler.crawl, url)),
        "whois": (lambda: _safe(whois_lookup.lookup_domain, domain)),
        "safe_browsing": (lambda: _safe(safe_browsing.check_url, url)),
        "openphish": (lambda: _safe(openphish.check_url, url)),
        "urlhaus": (lambda: _safe(urlhaus.check_url, url)),
        "urlscan": (lambda: _safe(urlscan_check.check_url, url)),
        "virustotal": (lambda: _safe(virustotal.check_url, url)),
        "crt_sh": (lambda: _safe(crtsh.check_domain, registrable_domain)),
        "dnstwist": (lambda: _safe(dnstwist_check.check_domain, registrable_domain)),
    }

    results = {}

    with ThreadPoolExecutor(max_workers=len(jobs) + 2) as executor:
        futures = {key: executor.submit(job) for key, job in jobs.items()}

        for key, future in futures.items():
            try:
                results[key] = future.result(timeout=SOURCE_TIMEOUT_SECONDS)
            except FutureTimeoutError:
                results[key] = {"source": key, "error": f"Timed out after {SOURCE_TIMEOUT_SECONDS}s"}

        # abuseipdb/shodan need the resolved IP, which only exists after
        # `whois` (which also resolves it) has come back -- run these two
        # concurrently with each other right after, rather than serially.
        ip_address = results.get("whois", {}).get("ip_address")

        ip_futures = {
            "abuseipdb": executor.submit(_safe, abuseipdb.check_ip, ip_address),
            "shodan": executor.submit(_safe, shodan_check.check_ip, ip_address),
        }

        for key, future in ip_futures.items():
            try:
                results[key] = future.result(timeout=SOURCE_TIMEOUT_SECONDS)
            except FutureTimeoutError:
                results[key] = {"source": key, "error": f"Timed out after {SOURCE_TIMEOUT_SECONDS}s"}

    verdict = scoring.score(results)

    return {
        "url": url,
        "domain": domain,
        "verdict": verdict,
        "sources": results,
    }


def analyze_url_stream(url: str):
    """
    Same checks as analyze_url(), but yields each source's result the
    moment it finishes instead of waiting for all of them -- this is
    what backs the "live updating" deep-analysis window on the
    frontend. Yields (event_type, payload) tuples:

        ("source", {"key": "safe_browsing", **result})   -- one per source, as it completes
        ("done",   {"verdict": {...}, "sources": {...}})  -- final message, once everything is in

    A slow source (usually urlscan/virustotal) never blocks the ones
    that finish faster -- results are yielded in completion order, not
    submission order.
    """
    domain = _extract_domain(url)
    registrable_domain = _registrable_domain(domain)
    results = {}

    jobs = {
        "crawl": (lambda: _safe(crawler.crawl, url)),
        "whois": (lambda: _safe(whois_lookup.lookup_domain, domain)),
        "safe_browsing": (lambda: _safe(safe_browsing.check_url, url)),
        "openphish": (lambda: _safe(openphish.check_url, url)),
        "urlhaus": (lambda: _safe(urlhaus.check_url, url)),
        "urlscan": (lambda: _safe(urlscan_check.check_url, url)),
        "virustotal": (lambda: _safe(virustotal.check_url, url)),
        "crt_sh": (lambda: _safe(crtsh.check_domain, registrable_domain)),
        "dnstwist": (lambda: _safe(dnstwist_check.check_domain, registrable_domain)),
    }

    with ThreadPoolExecutor(max_workers=len(jobs) + 2) as executor:
        future_to_key = {executor.submit(job): key for key, job in jobs.items()}

        # whois needs to be in hand before abuseipdb/shodan can be submitted,
        # so those two are added to the same pool once whois completes below.
        ip_futures_submitted = False

        for future in as_completed(future_to_key):
            key = future_to_key[future]
            try:
                result = future.result()
            except Exception as error:
                result = {"source": key, "error": str(error)}

            results[key] = result
            yield ("source", {"key": key, **(result if isinstance(result, dict) else {"value": result})})

            if key == "whois" and not ip_futures_submitted:
                ip_futures_submitted = True
                ip_address = result.get("ip_address") if isinstance(result, dict) else None

                ip_future_to_key = {
                    executor.submit(_safe, abuseipdb.check_ip, ip_address): "abuseipdb",
                    executor.submit(_safe, shodan_check.check_ip, ip_address): "shodan",
                }
                future_to_key.update(ip_future_to_key)
                # as_completed() was already given the original future set,
                # so newly submitted futures need their own wait loop below.
                for ip_future in as_completed(ip_future_to_key):
                    ip_key = ip_future_to_key[ip_future]
                    try:
                        ip_result = ip_future.result()
                    except Exception as error:
                        ip_result = {"source": ip_key, "error": str(error)}
                    results[ip_key] = ip_result
                    yield ("source", {"key": ip_key, **ip_result})

    verdict = scoring.score(results)
    yield ("done", {"verdict": verdict, "sources": results, "url": url, "domain": domain})


# ============================================================
# CLI WRAPPER
# ============================================================

def _print_report(result):
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("\nUsage:")
        print("python analyzer.py https://example.com\n")
        sys.exit(1)

    _print_report(analyze_url(sys.argv[1]))
