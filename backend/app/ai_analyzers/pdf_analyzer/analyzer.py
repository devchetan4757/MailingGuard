# analyzer.py

import re
import base64
from urllib.parse import urlparse

import pymupdf


# ============================================================
# RISKY WORDS / PHRASES
# ============================================================

RISKY_PATTERNS = {

    "Credential Request": [
        "enter your password",
        "verify your password",
        "confirm your password",
        "login to your account",
        "update your password",
        "password required",
        "verify your account",
        "confirm your account",
        "validate your account",
        "credentials"
    ],

    "Urgency": [
        "urgent",
        "immediately",
        "action required",
        "act now",
        "limited time",
        "within 24 hours",
        "within 48 hours",
        "your account will be suspended",
        "account suspension",
        "final warning",
        "respond immediately"
    ],

    "Financial Request": [
        "bank account",
        "credit card",
        "payment required",
        "send money",
        "wire transfer",
        "bank transfer",
        "invoice payment",
        "financial information",
        "payment details"
    ],

    "Social Engineering": [
        "confidential",
        "do not share",
        "keep this secret",
        "click here",
        "verify now",
        "download now",
        "enable content",
        "enable editing",
        "enable macros",
        "security alert"
    ],

    "Suspicious Request": [
        "personal information",
        "identity verification",
        "confirm your identity",
        "provide your details",
        "update your information",
        "security verification"
    ]
}


# ============================================================
# SUSPICIOUS PDF FEATURES
# ============================================================

PDF_FEATURE_PATTERNS = {
    "JavaScript": [
        b"/JavaScript",
        b"/JS"
    ],

    "Automatic Action": [
        b"/OpenAction",
        b"/AA"
    ],

    "Launch Action": [
        b"/Launch"
    ],

    "Embedded File": [
        b"/EmbeddedFile",
        b"/Filespec"
    ],

    "URI Action": [
        b"/URI"
    ],

    "Rich Media": [
        b"/RichMedia"
    ],

    "XFA Forms": [
        b"/XFA"
    ],

    "AcroForm": [
        b"/AcroForm"
    ]
}


URL_PATTERN = re.compile(
    r'(?i)\b('
    r'https?://[^\s<>"\'\]\)]+'
    r'|'
    r'www\.[^\s<>"\'\]\)]+'
    r')'
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_string(value):

    if value is None:
        return ""

    return str(value)


def normalize_url(url):

    if not url:
        return ""

    url = url.strip()

    while url and url[-1] in ".,;:!?":
        url = url[:-1]

    return url


def extract_urls_from_text(text):

    if not text:
        return []

    found_urls = []

    for match in URL_PATTERN.findall(text):

        url = normalize_url(match)

        if url:
            found_urls.append(url)

    return found_urls


def get_domain(url):

    try:

        test_url = url

        if not test_url.startswith("http"):
            test_url = "https://" + test_url

        parsed = urlparse(test_url)

        return parsed.netloc

    except Exception:
        return ""


def find_risky_words(text, page_number=None):

    if not text:
        return []

    results = []

    lower_text = text.lower()

    for category, phrases in RISKY_PATTERNS.items():

        for phrase in phrases:

            phrase_lower = phrase.lower()

            if phrase_lower not in lower_text:
                continue

            start_index = 0

            while True:

                position = lower_text.find(
                    phrase_lower,
                    start_index
                )

                if position == -1:
                    break

                context_start = max(
                    0,
                    position - 80
                )

                context_end = min(
                    len(text),
                    position + len(phrase) + 120
                )

                context = text[
                    context_start:context_end
                ].strip()

                result = {
                    "keyword": phrase,
                    "category": category,
                    "context": context
                }

                if page_number is not None:
                    result["page"] = page_number

                results.append(result)

                start_index = position + len(phrase_lower)

    return results


def split_into_sections(text):

    if not text:
        return []

    paragraphs = re.split(
        r'\n\s*\n+',
        text
    )

    sections = []

    for paragraph in paragraphs:

        paragraph = paragraph.strip()

        if paragraph:
            sections.append(paragraph)

    if len(sections) <= 1:

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        sections = lines

    return sections


def analyze_suspicious_sections(text, page_number):

    suspicious_sections = []

    sections = split_into_sections(text)

    for index, section in enumerate(sections):

        section_lower = section.lower()

        detected_categories = []
        detected_keywords = []

        for category, phrases in RISKY_PATTERNS.items():

            category_found = False

            for phrase in phrases:

                if phrase.lower() in section_lower:

                    detected_keywords.append(
                        phrase
                    )

                    category_found = True

            if category_found:
                detected_categories.append(
                    category
                )

        url_count = len(
            extract_urls_from_text(section)
        )

        risk_score = (
            len(detected_keywords)
            + url_count
        )

        if risk_score == 0:
            continue

        suspicious_sections.append({
            "page": page_number,
            "paragraph_number": index + 1,
            "risk_score": min(risk_score, 10),
            "categories": detected_categories,
            "keywords": detected_keywords,
            "text": section[:2500]
        })

    return suspicious_sections


def detect_pdf_features(pdf_bytes):

    detected_features = []

    lower_bytes = pdf_bytes.lower()

    for feature_name, patterns in PDF_FEATURE_PATTERNS.items():

        found = False

        for pattern in patterns:

            if pattern.lower() in lower_bytes:
                found = True
                break

        if found:

            detected_features.append({
                "category": feature_name,
                "description": (
                    f"PDF structure contains indicator: "
                    f"{feature_name}"
                )
            })

    return detected_features


def make_image_data_uri(image_bytes, extension):

    if not image_bytes:
        return ""

    extension = safe_string(extension).lower()

    mime_types = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "jp2": "image/jp2",
        "jpx": "image/jp2",
        "tiff": "image/tiff",
        "bmp": "image/bmp"
    }

    mime_type = mime_types.get(
        extension,
        "image/png"
    )

    encoded = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    return (
        f"data:{mime_type};base64,"
        f"{encoded}"
    )


# ============================================================
# MAIN PDF ANALYZER
# ============================================================

def analyze_pdf(pdf_bytes, filename="uploaded.pdf"):

    result = {
        "file": {
            "name": filename,
            "size_bytes": len(pdf_bytes),
            "pages": 0
        },

        "metadata": {},

        "risky_words": [],

        "suspicious_paragraphs": [],

        "urls": [],

        "clickable_links": [],

        "images": [],

        "attachments": [],

        "suspicious_features": [],

        "pages": [],

        "summary": {
            "status": "Low Risk",
            "indicator_score": 0,
            "total_risky_words": 0,
            "total_suspicious_paragraphs": 0,
            "total_urls": 0,
            "total_images": 0,
            "total_attachments": 0,
            "total_features": 0
        }
    }

    doc = None

    try:

        # Open PDF directly from memory.
        # No uploaded PDF file is saved to disk.
        doc = pymupdf.open(
            stream=pdf_bytes,
            filetype="pdf"
        )

        result["file"]["pages"] = len(doc)

        # ====================================================
        # METADATA
        # ====================================================

        metadata = doc.metadata or {}

        for key, value in metadata.items():

            if value not in (
                None,
                "",
                "None"
            ):

                result["metadata"][key] = (
                    safe_string(value)
                )

        # ====================================================
        # PDF FEATURES
        # ====================================================

        result["suspicious_features"] = (
            detect_pdf_features(pdf_bytes)
        )

        # ====================================================
        # EMBEDDED ATTACHMENTS
        # ====================================================

        try:

            attachment_names = doc.embfile_names()

            for attachment_name in attachment_names:

                result["attachments"].append({
                    "name": safe_string(
                        attachment_name
                    )
                })

        except Exception:
            pass

        # ====================================================
        # URL DEDUPLICATION
        # ====================================================

        found_urls = set()
        found_clickable_links = set()

        # ====================================================
        # IMAGE COUNTER
        # ====================================================

        image_counter = 0

        # ====================================================
        # ANALYZE EACH PAGE
        # ====================================================

        for page_index in range(len(doc)):

            page = doc[page_index]

            page_number = page_index + 1

            # ------------------------------------------------
            # TEXT
            # ------------------------------------------------

            try:

                page_text = page.get_text(
                    "text"
                ) or ""

            except Exception:

                page_text = ""

            # ------------------------------------------------
            # PAGE STATISTICS
            # ------------------------------------------------

            words = re.findall(
                r"\b[\w'-]+\b",
                page_text
            )

            result["pages"].append({
                "page": page_number,
                "words": len(words),
                "characters": len(page_text)
            })

            # ------------------------------------------------
            # RISKY WORDS
            # ------------------------------------------------

            risky_matches = find_risky_words(
                page_text,
                page_number
            )

            result["risky_words"].extend(
                risky_matches
            )

            # ------------------------------------------------
            # SUSPICIOUS PARAGRAPHS
            # ------------------------------------------------

            suspicious_sections = (
                analyze_suspicious_sections(
                    page_text,
                    page_number
                )
            )

            result[
                "suspicious_paragraphs"
            ].extend(
                suspicious_sections
            )

            # ------------------------------------------------
            # URLs FOUND IN TEXT
            # ------------------------------------------------

            text_urls = extract_urls_from_text(
                page_text
            )

            for url in text_urls:

                normalized = url.lower()

                if normalized in found_urls:
                    continue

                found_urls.add(normalized)

                result["urls"].append({
                    "url": url,
                    "domain": get_domain(url),
                    "page": page_number,
                    "source": "PDF text"
                })

            # ------------------------------------------------
            # CLICKABLE PDF LINKS
            # ------------------------------------------------

            try:

                links = page.get_links()

            except Exception:

                links = []

            for link in links:

                uri = safe_string(
                    link.get("uri")
                ).strip()

                if not uri:
                    continue

                normalized = uri.lower()

                if normalized in found_clickable_links:
                    continue

                found_clickable_links.add(
                    normalized
                )

                result[
                    "clickable_links"
                ].append({
                    "url": uri,
                    "domain": get_domain(uri),
                    "page": page_number
                })

                if normalized not in found_urls:

                    found_urls.add(normalized)

                    result["urls"].append({
                        "url": uri,
                        "domain": get_domain(uri),
                        "page": page_number,
                        "source": "Clickable PDF link"
                    })

            # ------------------------------------------------
            # IMAGES
            # ------------------------------------------------

            try:

                page_images = page.get_images(
                    full=True
                )

            except Exception:

                page_images = []

            page_seen_xrefs = set()

            for image_info in page_images:

                if not image_info:
                    continue

                xref = image_info[0]

                if xref in page_seen_xrefs:
                    continue

                page_seen_xrefs.add(xref)

                try:

                    extracted_image = (
                        doc.extract_image(xref)
                    )

                    image_bytes = (
                        extracted_image.get(
                            "image",
                            b""
                        )
                    )

                    image_extension = (
                        extracted_image.get(
                            "ext",
                            "png"
                        )
                    )

                    width = extracted_image.get(
                        "width",
                        0
                    )

                    height = extracted_image.get(
                        "height",
                        0
                    )

                    if not image_bytes:
                        continue

                    image_data = (
                        make_image_data_uri(
                            image_bytes,
                            image_extension
                        )
                    )

                    if not image_data:
                        continue

                    image_counter += 1

                    result["images"].append({
                        "id": image_counter,
                        "page": page_number,
                        "width": width,
                        "height": height,
                        "format": image_extension,
                        "data": image_data
                    })

                except Exception as image_error:

                    print(
                        f"Could not read image "
                        f"on page {page_number}: "
                        f"{image_error}"
                    )

        # ====================================================
        # REMOVE DUPLICATE RISKY MATCHES
        # ====================================================

        unique_risky = []
        risky_seen = set()

        for item in result["risky_words"]:

            identifier = (
                item.get("keyword", "").lower(),
                item.get("category", "").lower(),
                item.get("page"),
                item.get("context", "")[:150]
            )

            if identifier in risky_seen:
                continue

            risky_seen.add(identifier)
            unique_risky.append(item)

        result["risky_words"] = unique_risky

        # ====================================================
        # RISK SCORE
        # ====================================================

        risky_word_count = len(
            result["risky_words"]
        )

        suspicious_section_count = len(
            result["suspicious_paragraphs"]
        )

        url_count = len(
            result["urls"]
        )

        attachment_count = len(
            result["attachments"]
        )

        feature_count = len(
            result["suspicious_features"]
        )

        image_count = len(
            result["images"]
        )

        raw_score = 0

        # Risky phrases
        raw_score += min(
            risky_word_count,
            10
        )

        # Suspicious text sections
        raw_score += min(
            suspicious_section_count * 2,
            10
        )

        # PDF features
        raw_score += feature_count * 2

        # Embedded attachments
        raw_score += attachment_count * 3

        # URLs
        if url_count > 0:
            raw_score += min(
                url_count,
                5
            )

        # Final score 0 - 10
        indicator_score = min(
            raw_score,
            10
        )

        if indicator_score >= 8:

            status = "High Risk"

        elif indicator_score >= 4:

            status = "Medium Risk"

        else:

            status = "Low Risk"

        result["summary"] = {
            "status": status,

            "indicator_score": indicator_score,

            "total_risky_words": risky_word_count,

            "total_suspicious_paragraphs":
                suspicious_section_count,

            "total_urls": url_count,

            "total_images": image_count,

            "total_attachments": attachment_count,

            "total_features": feature_count
        }

        return result

    finally:

        if doc is not None:

            try:
                doc.close()

            except Exception:
                pass