# whois_lookup.py

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


def print_dns_records(domain):
    print("\n[ DNS INFORMATION ]")
    print("-" * 60)

    record_types = ["A", "AAAA", "MX", "NS", "TXT"]

    for record_type in record_types:
        records = get_dns_records(domain, record_type)

        print(f"\n{record_type} Records:")

        if records:
            for record in records:
                print(f"  - {record}")
        else:
            print("  Not Available")


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

    # Clean URL
    domain = domain.strip()
    domain = domain.replace("https://", "")
    domain = domain.replace("http://", "")
    domain = domain.replace("www.", "")
    domain = domain.split("/")[0]

    print("\n" + "=" * 70)
    print("                 DOMAIN WHOIS INTELLIGENCE REPORT")
    print("=" * 70)

    print(f"\nTarget Domain : {domain}")
    print(f"Scan Time     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # NETWORK INFORMATION
    print("\n[ NETWORK INFORMATION ]")
    print("-" * 70)

    ip_address = get_ip_address(domain)

    print("IP Address    :", ip_address)

    # WHOIS INFORMATION
    try:
        result = whois.whois(domain)

        creation_date = result.creation_date
        expiration_date = result.expiration_date

        print("\n[ DOMAIN INFORMATION ]")
        print("-" * 70)

        print("Domain Name   :", safe_value(result.domain_name))
        print("Registrar     :", safe_value(result.registrar))
        print("WHOIS Server  :", safe_value(result.whois_server))
        print("Creation Date :", safe_value(creation_date))
        print("Updated Date  :", safe_value(result.updated_date))
        print("Expiry Date   :", safe_value(expiration_date))
        print("Domain Age    :", get_domain_age(creation_date))

        print("\n[ DOMAIN STATUS ]")
        print("-" * 70)

        print("Status        :", safe_value(result.status))

        print("\n[ NAME SERVERS ]")
        print("-" * 70)

        name_servers = result.name_servers

        if name_servers:
            if isinstance(name_servers, (list, tuple, set)):
                for server in name_servers:
                    print(" -", server)
            else:
                print(" -", name_servers)
        else:
            print("Not Available")

        print("\n[ PUBLIC REGISTRANT INFORMATION ]")
        print("-" * 70)

        print("Organization  :", safe_value(result.org))
        print("Country       :", safe_value(result.country))
        print("State         :", safe_value(result.state))
        print("City          :", safe_value(result.city))

        # SECURITY OBSERVATIONS
        warnings = analyze_domain(
            creation_date,
            expiration_date
        )

        print("\n[ SECURITY OBSERVATIONS ]")
        print("-" * 70)

        if warnings:
            for warning in warnings:
                print("WARNING:", warning)
        else:
            print("No basic domain age or expiry warnings detected.")

    except Exception as error:
        print("\n[ WHOIS LOOKUP ERROR ]")
        print("-" * 70)
        print(error)

    # DNS INFORMATION
    print_dns_records(domain)

    print("\n" + "=" * 70)
    print("                    END OF REPORT")
    print("=" * 70 + "\n")


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("\nUsage:")
        print("python whois_lookup.py example.com\n")
        sys.exit(1)

    lookup_domain(sys.argv[1])