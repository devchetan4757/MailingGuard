# whois_lookup.py
#
# Backend-only version.
# Original script only printed a report to the terminal.
# `lookup_domain()` now returns a structured dict so an AI layer
# (or any other caller) can consume the result programmatically.
# A thin CLI wrapper is kept at the bottom for manual testing.

import sys
import socket
from datetime import datetime, timezone

import whois
import dns.resolver


def safe_value(value):
    if value is None:
        return "Not Available"

    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value)

    return str(value)


def get_first_date(date_value):
    """WHOIS sometimes returns a list of dates."""
    if isinstance(date_value, list):
        return date_value[0] if date_value else None
    return date_value


def get_domain_age(creation_date):
    creation_date = get_first_date(creation_date)

    if not creation_date:
        return "Not Available"

    try:
        if creation_date.tzinfo is None:
            creation_date = creation_date.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age = now - creation_date

        years = age.days // 365
        days = age.days % 365

        return f"{years} years, {days} days"

    except Exception:
        return "Could not calculate"


def get_ip_address(domain):
    try:
        return socket.gethostbyname(domain)
    except socket.gaierror:
        return "Could not resolve IP address"


def get_dns_records(domain, record_type):
    try:
        answers = dns.resolver.resolve(domain, record_type)
        return [str(answer) for answer in answers]

    except Exception:
        return []


def get_all_dns_records(domain):
    record_types = ["A", "AAAA", "MX", "NS", "TXT"]

    return {
        record_type: get_dns_records(domain, record_type)
        for record_type in record_types
    }


def analyze_domain(creation_date, expiration_date):
    warnings = []

    creation_date = get_first_date(creation_date)
    expiration_date = get_first_date(expiration_date)

    now = datetime.now(timezone.utc)

    if creation_date:
        try:
            if creation_date.tzinfo is None:
                creation_date = creation_date.replace(tzinfo=timezone.utc)

            age_days = (now - creation_date).days

            if age_days < 30:
                warnings.append(
                    "Domain is very new (less than 30 days old)."
                )
            elif age_days < 180:
                warnings.append(
                    "Domain is relatively new (less than 6 months old)."
                )

        except Exception:
            pass

    if expiration_date:
        try:
            if expiration_date.tzinfo is None:
                expiration_date = expiration_date.replace(tzinfo=timezone.utc)

            days_until_expiry = (expiration_date - now).days

            if 0 <= days_until_expiry < 30:
                warnings.append(
                    "Domain registration expires within 30 days."
                )

        except Exception:
            pass

    return warnings


def lookup_domain(domain):
    """
    Run a WHOIS + DNS + basic risk analysis on a domain and return
    the result as a structured dict. This is the function the AI
    layer should import and call directly.
    """

    # Clean URL
    domain = domain.strip()
    domain = domain.replace("https://", "")
    domain = domain.replace("http://", "")
    domain = domain.replace("www.", "")
    domain = domain.split("/")[0]

    result = {
        "domain": domain,
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "ip_address": get_ip_address(domain),
        "whois": {},
        "warnings": [],
        "dns_records": {},
        "error": None
    }

    try:
        whois_result = whois.whois(domain)

        creation_date = whois_result.creation_date
        expiration_date = whois_result.expiration_date

        name_servers = whois_result.name_servers

        if name_servers and not isinstance(name_servers, (list, tuple, set)):
            name_servers = [name_servers]

        result["whois"] = {
            "domain_name": safe_value(whois_result.domain_name),
            "registrar": safe_value(whois_result.registrar),
            "whois_server": safe_value(whois_result.whois_server),
            "creation_date": safe_value(creation_date),
            "updated_date": safe_value(whois_result.updated_date),
            "expiration_date": safe_value(expiration_date),
            "domain_age": get_domain_age(creation_date),
            "status": safe_value(whois_result.status),
            "name_servers": list(name_servers) if name_servers else [],
            "organization": safe_value(whois_result.org),
            "country": safe_value(whois_result.country),
            "state": safe_value(whois_result.state),
            "city": safe_value(whois_result.city)
        }

        result["warnings"] = analyze_domain(
            creation_date,
            expiration_date
        )

    except Exception as error:
        result["error"] = str(error)

    result["dns_records"] = get_all_dns_records(domain)

    return result


# ============================================================
# OPTIONAL CLI WRAPPER (manual testing only, not used by the AI layer)
# ============================================================

def _print_report(result):
    import json
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("\nUsage:")
        print("python whois_lookup.py example.com\n")
        sys.exit(1)

    _print_report(lookup_domain(sys.argv[1]))
