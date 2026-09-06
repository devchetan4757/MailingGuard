# dnstwist_check.py
#
# dnstwist generates typo/homoglyph/bitsquat permutations of a domain
# (e.g. paypa1.com, arnazon.com) and checks which ones are actually
# registered and resolving -- catches lookalike domains that a plain
# WHOIS-on-the-exact-domain check would never find.
#
# Requires: pip install dnstwist --break-system-packages
# Run as a subprocess (not imported as a library) because it can take
# a while to resolve dozens of permutations, and we don't want a slow
# or hanging dnstwist run to affect the rest of this process.
#
# Speed: dnstwist's own default thread count is min(32, os.cpu_count() + 4)
# -- on a small/shared container (1-2 vCPUs) that's only 5-6 threads doing
# DNS resolution across 100+ generated permutations, several record types
# each, with retries on ones that don't resolve. That regularly runs past
# 60s. --threads and --nameservers below are the two levers that actually
# fix this (raising the timeout just waits longer for the same slow run).

import json
import os
import subprocess
import sys

try:
    from . import config
except ImportError:
    import config

# The outer analyzer (analyzer.py) gives every source up to
# SOURCE_TIMEOUT_SECONDS = 65s before it gives up and reports a timeout
# itself. Leave a small buffer under that ceiling so this process's own
# timeout message (with real detail) fires first instead of the generic
# outer one.
SUBPROCESS_TIMEOUT_SECONDS = int(os.environ.get("DNSTWIST_TIMEOUT_SECONDS", "55"))

# Force a higher thread count than dnstwist's own cpu-based default --
# this is the main lever for actually finishing within the timeout on a
# small container. Override with DNSTWIST_THREADS if this host is even
# more constrained (or can handle more).
DNSTWIST_THREADS = os.environ.get("DNSTWIST_THREADS", "50")

# Point at fast, high-volume-tolerant public resolvers instead of
# whatever this host's default resolver is -- a slow, low-rate-limit, or
# ISP/cloud-internal resolver is the other big source of dnstwist being
# slow (each of the ~100+ permutations needs its own NXDOMAIN or
# resolved answer). Override with DNSTWIST_NAMESERVERS (comma-separated)
# if these are blocked/undesirable on this network.
DNSTWIST_NAMESERVERS = os.environ.get("DNSTWIST_NAMESERVERS", "1.1.1.1,8.8.8.8")


def check_domain(domain: str) -> dict:
    cmd = [
        sys.executable, "-m", "dnstwist",
        "--format", "json",
        "--registered",
        "--threads", DNSTWIST_THREADS,
    ]
    if DNSTWIST_NAMESERVERS:
        cmd += ["--nameservers", DNSTWIST_NAMESERVERS]
    cmd.append(domain)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {
            "source": "dnstwist",
            "error": (
                f"Timed out after {SUBPROCESS_TIMEOUT_SECONDS}s even with --threads "
                f"{DNSTWIST_THREADS} and --nameservers {DNSTWIST_NAMESERVERS}. Try raising "
                "DNSTWIST_THREADS further, or set DNSTWIST_TIMEOUT_SECONDS higher (and raise "
                "analyzer.py's SOURCE_TIMEOUT_SECONDS to match) if this domain just generates "
                "an unusually large permutation set."
            ),
        }
    except FileNotFoundError:
        return {"source": "dnstwist", "error": "dnstwist not installed (pip install dnstwist --break-system-packages)"}

    if result.returncode != 0 and not result.stdout.strip():
        stderr = result.stderr.strip()
        # "No module named dnstwist" almost always means dnstwist was
        # installed into a different Python than the one running this
        # app (e.g. installed system-wide with --break-system-packages
        # while the app itself runs inside a venv) -- sys.executable
        # here is *this* process's interpreter, so if dnstwist isn't on
        # its sys.path, this is what you get instead of FileNotFoundError.
        if "No module named" in stderr and "dnstwist" in stderr:
            stderr += (
                f" -- dnstwist isn't installed for the Python running this app ({sys.executable}). "
                f"Run `{sys.executable} -m pip install dnstwist` (add --break-system-packages only if "
                "this interpreter is NOT a venv) so it lands in the same environment, not a different one."
            )
        return {"source": "dnstwist", "error": stderr or "dnstwist produced no output"}

    try:
        permutations = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"source": "dnstwist", "error": "Could not parse dnstwist output"}

    # Original domain itself is included in dnstwist's output -- exclude it
    lookalikes = [p for p in permutations if p.get("domain", "").lower() != domain.lower()]

    return {
        "source": "dnstwist",
        "original_domain": domain,
        "registered_lookalike_count": len(lookalikes),
        # Standard boolean field name every other analyzer in this package
        # uses (see safe_browsing/urlhaus/openphish's "listed"/"malicious"
        # and the frontend's isFlagged()) -- without this, the UI has no
        # generic field to key off of and always renders dnstwist as
        # "Clean" no matter how many lookalikes it actually finds.
        "flagged": len(lookalikes) > 0,
        "lookalikes": lookalikes,
    }

    if result.returncode != 0 and not result.stdout.strip():
        stderr = result.stderr.strip()
        # "No module named dnstwist" almost always means dnstwist was
        # installed into a different Python than the one running this
        # app (e.g. installed system-wide with --break-system-packages
        # while the app itself runs inside a venv) -- sys.executable
        # here is *this* process's interpreter, so if dnstwist isn't on
        # its sys.path, this is what you get instead of FileNotFoundError.
        if "No module named" in stderr and "dnstwist" in stderr:
            stderr += (
                f" -- dnstwist isn't installed for the Python running this app ({sys.executable}). "
                f"Run `{sys.executable} -m pip install dnstwist` (add --break-system-packages only if "
                "this interpreter is NOT a venv) so it lands in the same environment, not a different one."
            )
        return {"source": "dnstwist", "error": stderr or "dnstwist produced no output"}

    try:
        permutations = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"source": "dnstwist", "error": "Could not parse dnstwist output"}

    # Original domain itself is included in dnstwist's output -- exclude it
    lookalikes = [p for p in permutations if p.get("domain", "").lower() != domain.lower()]

    return {
        "source": "dnstwist",
        "original_domain": domain,
        "registered_lookalike_count": len(lookalikes),
        # Standard boolean field name every other analyzer in this package
        # uses (see safe_browsing/urlhaus/openphish's "listed"/"malicious"
        # and the frontend's isFlagged()) -- without this, the UI has no
        # generic field to key off of and always renders dnstwist as
        # "Clean" no matter how many lookalikes it actually finds.
        "flagged": len(lookalikes) > 0,
        "lookalikes": lookalikes,
    }
