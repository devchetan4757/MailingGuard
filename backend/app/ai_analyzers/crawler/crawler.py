import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


def fetch_html(url, timeout=10):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; SimpleCrawler/1.0)"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=timeout
    )

    response.raise_for_status()

    return response.text


def get_title(soup):
    tag = soup.find("title")
    return tag.get_text(strip=True) if tag else None


def get_meta_description(soup):
    tag = soup.find(
        "meta",
        attrs={"name": "description"}
    )

    if tag and tag.get("content"):
        return tag["content"].strip()

    tag = soup.find(
        "meta",
        attrs={"property": "og:description"}
    )

    if tag and tag.get("content"):
        return tag["content"].strip()

    return None


def get_links(soup, base_url):
    links = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()

        if (
            not href
            or href.startswith("#")
            or href.startswith("javascript:")
            or href.startswith("mailto:")
        ):
            continue

        absolute = urljoin(base_url, href)

        if absolute not in seen:
            seen.add(absolute)

            links.append({
                "url": absolute,
                "text": a.get_text(strip=True),
                "internal": (
                    urlparse(absolute).netloc
                    == urlparse(base_url).netloc
                )
            })

    return links


def crawl(url):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    links = get_links(soup, url)

    return {
        "url": url,
        "title": get_title(soup),
        "meta_description": get_meta_description(soup),
        "link_count": len(links),
        "links": links,
        "html": html
    }