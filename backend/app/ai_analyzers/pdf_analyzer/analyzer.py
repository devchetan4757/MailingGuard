# analyzer.py

import re
import io
import base64
from urllib.parse import urlparse

import pymupdf

try:
    from . import virustotal_file
except ImportError:
    import virustotal_file

try:
    from . import structure_checks
except ImportError:
    import structure_checks

try:
    from . import metadata_forensics
except ImportError:
    import metadata_forensics

# QR / 2D barcode decoding for embedded images. Optional dependency --
# if pyzbar (or the underlying libzbar system library) isn't
# installed, QR decoding is silently skipped rather than breaking the
# rest of the analyzer. See requirements.txt for the pip package and
# the required `libzbar0` system package.
try:
    from pyzbar.pyzbar import decode as decode_barcodes
    from PIL import Image
    QR_DECODING_AVAILABLE = True
except ImportError:
    QR_DECODING_AVAILABLE = False


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


# ============================================================
# SUSPICIOUS JAVASCRIPT API CALLS
# ============================================================
# Function/method names that show up disproportionately often in
# malicious PDF JavaScript vs. the legitimate uses of PDF JS (form
# field math, print dialogs, etc). A hit here doesn't prove malice
# on its own -- these are also occasionally used legitimately -- but
# it's a much stronger signal than "the PDF merely contains a /JS
# key somewhere", which is the old presence-only check this replaces.

SUSPICIOUS_JS_CALLS = {
    "eval": (
        "Dynamic code execution -- commonly used to deobfuscate and "
        "run a payload that was hidden from static scanners"
    ),
    "unescape": (
        "URL-style decoding, frequently paired with eval() to smuggle "
        "obfuscated shellcode or script past text-based filters"
    ),
    "String.fromCharCode": (
        "Builds strings from character codes, a common obfuscation "
        "technique paired with eval() to hide payload contents"
    ),
    "App.alert": (
        "Native dialog call; shows up in exploit proof-of-concepts as "
        "a harmless-looking canary before/after a real payload runs"
    ),
    "this.exportDataObject": (
        "Silently writes an embedded file out to disk -- a way to "
        "drop a payload without further user interaction"
    ),
    "Collab.getIcon": (
        "Known exploit trigger for CVE-2009-0927 (Adobe Reader "
        "Collab.getIcon buffer overflow)"
    ),
    "Collab.collectEmailInfo": (
        "Known exploit trigger for CVE-2007-5659 "
        "(Collab.collectEmailInfo buffer overflow)"
    ),
    "util.printf": (
        "String formatting function abused for heap grooming in "
        "several Reader exploits (e.g. CVE-2008-2992)"
    ),
    "spell.customDictionaryOpen": (
        "Known exploit trigger for CVE-2009-1493 "
        "(spell-check buffer overflow)"
    ),
    "media.newPlayer": (
        "Known exploit trigger used in Adobe media-player related "
        "Reader vulnerabilities"
    ),
    "getAnnots": (
        "Used in several exploit chains for heap spraying via "
        "crafted annotation objects"
    ),
    "getIcon": (
        "Icon-handling call related to the Collab.getIcon exploit "
        "family"
    ),
    "getPageNthWord": (
        "Used in Adobe Reader font/glyph parsing exploit chains "
        "(e.g. CVE-2010-0188 style heap spray setups)"
    ),
}

# A hit on any of these is treated as strong evidence on its own --
# not just "suspicious", but a documented exploit trigger -- and is
# enough to force the overall verdict to High Risk regardless of the
# rest of the local heuristic score.
KNOWN_CVE_TRIGGER_CALLS = {
    "Collab.getIcon",
    "Collab.collectEmailInfo",
    "spell.customDictionaryOpen",
    "media.newPlayer",
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


def find_suspicious_js_calls(script_text):

    if not script_text:
        return []

    found = []

    for call_name, description in SUSPICIOUS_JS_CALLS.items():

        # Word-boundary-ish match so "eval" doesn't fire on
        # "evaluate" etc, while still matching dotted calls like
        # "Collab.getIcon" or "App.alert" as literal substrings.
        pattern = re.compile(
            r'(?<![\w.])' + re.escape(call_name) + r'\s*\(',
            re.IGNORECASE
        )

        if pattern.search(script_text):

            found.append({
                "call": call_name,
                "description": description,
                "known_cve_trigger": call_name in KNOWN_CVE_TRIGGER_CALLS
            })

    return found


def extract_javascript(doc):
    """
    Pull the actual JavaScript source out of a PDF, rather than just
    flagging that the "/JavaScript" or "/JS" byte string is present
    somewhere in the file.

    JavaScript in a PDF is attached via a /JS key, whose value is
    EITHER:
      - a literal PDF string containing the script directly, or
      - an indirect reference to a separate stream object that
        contains the script (used when the script is long).

    We walk every object in the xref table and use PyMuPDF's
    xref_get_key() to read that object's /JS entry (if any), which
    handles PDF string escaping for us. If /JS points to another
    object, we follow the reference and decompress that object's
    stream to get the script text.
    """

    scripts = []

    try:
        xref_count = doc.xref_length()
    except Exception:
        return scripts

    seen_xrefs = set()

    for xref in range(1, xref_count):

        try:
            key_type, key_value = doc.xref_get_key(xref, "JS")
        except Exception:
            continue

        if key_type in ("null", None) or not key_value:
            continue

        script_text = None

        try:

            if key_type == "string":

                # PyMuPDF already unescapes PDF string syntax for us.
                script_text = key_value

            elif key_type == "xref":

                # key_value looks like "12 0 R" -- the JS lives in a
                # separate (usually stream) object.
                ref_xref = int(key_value.split()[0])

                if doc.xref_is_stream(ref_xref):

                    raw_stream = doc.xref_stream(ref_xref)

                    if raw_stream:
                        script_text = raw_stream.decode(
                            "utf-8",
                            errors="replace"
                        )

                else:

                    # Rare: an indirect reference to a plain string
                    # object rather than a stream. Fall back to
                    # reading it the same way.
                    try:
                        _, nested_value = doc.xref_get_key(
                            ref_xref,
                            "JS"
                        )
                        script_text = nested_value or None
                    except Exception:
                        script_text = None

        except Exception:
            script_text = None

        if not script_text:
            continue

        if xref in seen_xrefs:
            continue

        seen_xrefs.add(xref)

        truncated = len(script_text) > 5000

        scripts.append({
            "xref": xref,
            "length": len(script_text),
            "script": script_text[:5000],
            "truncated": truncated,
            "suspicious_calls": find_suspicious_js_calls(script_text)
        })

    return scripts


# ============================================================
# QR CODES IN EMBEDDED IMAGES
# ============================================================
# Phishing PDFs increasingly hide the malicious link inside a QR
# code image ("scan to verify your account") instead of a clickable
# /URI action or plain text link, specifically to dodge text-based
# URL scanners and "contains a link" heuristics -- a human sees a
# link, but nothing in get_text() or get_links() shows one.
#
# We decode every embedded image for QR (or other 2D barcode)
# payloads and feed any URL found straight into the same `urls` list
# that PDF text and clickable links feed into. That list is what
# deep_analysis.py's _analyze_pdf_urls() fans out to analyze_url()
# (VirusTotal / Safe Browsing / urlscan / WHOIS / dnstwist), so a
# QR-hidden link gets identical treatment with no extra wiring.

def decode_qr_codes_from_image(image_bytes):
    """
    Attempt to decode any barcodes (QR or otherwise) present in a
    single embedded image.

    Returns a list of {"type": "QRCODE", "data": "<decoded text>"}
    dicts. Never raises: a corrupt/unsupported image, or the
    pyzbar/Pillow dependency being unavailable, just yields no
    results rather than failing the whole PDF analysis.
    """

    if not QR_DECODING_AVAILABLE:
        return []

    if not image_bytes:
        return []

    try:
        pil_image = Image.open(io.BytesIO(image_bytes))
        pil_image.load()
    except Exception:
        return []

    try:
        # zbar chokes on some palette (P-mode), CMYK, and 1-bit modes
        # that PDFs commonly embed images in -- normalize first.
        if pil_image.mode not in ("L", "RGB"):
            pil_image = pil_image.convert("RGB")
    except Exception:
        pass

    try:
        barcodes = decode_barcodes(pil_image)
    except Exception:
        return []

    results = []

    for barcode in barcodes:

        try:
            payload = barcode.data.decode(
                "utf-8",
                errors="replace"
            )
        except Exception:
            continue

        if not payload:
            continue

        results.append({
            "type": safe_string(
                getattr(barcode, "type", "") or "BARCODE"
            ),
            "data": payload
        })

    return results


# ============================================================
# INVISIBLE / TINY-FONT TEXT (KEYWORD STUFFING)
# ============================================================
# Phishing kits sometimes stuff extra keywords -- brand names,
# "verify your account", etc -- into a PDF using text that a human
# will never see: font sizes far below readable (e.g. 0.1pt) or a
# fill color that matches a plain white page (white-on-white). The
# text is fully present for get_text() and any filter that reads it,
# but invisible on screen/print, so it's used either to fool a human
# skimming the rendered page after a text-based filter already
# cleared the file, or to pad/poison automated keyword scanners.
#
# PyMuPDF's "dict" text extraction mode gives per-span font size and
# fill color for free, so this reuses the same page.get_text() call
# style as the rest of the page loop above -- no extra rendering or
# rasterization needed.

# Below this size a span is not realistically legible at any normal
# zoom/print level -- this is the "0.1pt" style hidden-text case.
TINY_FONT_SIZE_THRESHOLD = 1.0

# Below this size the text is technically legible but far smaller
# than any normal body/footnote text -- flagged at lower severity.
SMALL_FONT_SIZE_THRESHOLD = 3.0

# A color channel at/above this value (0-255 scale) is treated as
# "white enough" that text in it will be invisible against a plain
# white page background, which is the overwhelmingly common PDF page
# color. This is a heuristic, not a true background-color check --
# PyMuPDF's fast text dict doesn't expose the actual rendered
# background under a given span.
NEAR_WHITE_CHANNEL_THRESHOLD = 250


def _color_int_to_rgb(color_int):
    """
    PyMuPDF's get_text("dict") encodes span fill color as a single
    sRGB integer (0xRRGGBB). Convert to an (r, g, b) tuple, each
    0-255. Anything that isn't a plausible color int (missing,
    negative, out of range) falls back to black -- i.e. "not
    suspicious" -- rather than raising.
    """

    try:
        value = int(color_int)
    except (TypeError, ValueError):
        return (0, 0, 0)

    if value < 0:
        return (0, 0, 0)

    red = (value >> 16) & 0xFF
    green = (value >> 8) & 0xFF
    blue = value & 0xFF

    return (red, green, blue)


def detect_hidden_text(page, page_number):
    """
    Walk every text span on a page and flag ones that are present in
    the extracted text but effectively invisible to a human reader:
    font size below normal legibility, and/or a fill color close
    enough to white to disappear against a plain page background.

    Returns a list of finding dicts, each describing one flagged
    span (page, the hidden text itself, font/size/color, why it was
    flagged, and a severity).
    """

    findings = []

    try:
        text_dict = page.get_text("dict") or {}
    except Exception:
        return findings

    for block in text_dict.get("blocks", []):

        # type 0 = text block, type 1 = image block -- only text
        # blocks have "lines"/"spans" to walk.
        if block.get("type") != 0:
            continue

        for line in block.get("lines", []):

            for span in line.get("spans", []):

                span_text = span.get("text", "")

                if not span_text or not span_text.strip():
                    continue

                size = span.get("size") or 0
                rgb = _color_int_to_rgb(span.get("color"))

                is_tiny = size < TINY_FONT_SIZE_THRESHOLD
                is_small = (
                    not is_tiny
                    and size < SMALL_FONT_SIZE_THRESHOLD
                )
                is_near_white = all(
                    channel >= NEAR_WHITE_CHANNEL_THRESHOLD
                    for channel in rgb
                )

                if not (is_tiny or is_small or is_near_white):
                    continue

                reasons = []

                if is_tiny:
                    reasons.append(
                        f"font size {size:.2f}pt is far below "
                        f"legible size -- effectively invisible text"
                    )
                elif is_small:
                    reasons.append(
                        f"font size {size:.2f}pt is unusually "
                        f"small for readable body/footnote text"
                    )

                if is_near_white:
                    reasons.append(
                        f"fill color rgb{rgb} is white/near-white "
                        f"and will not render visibly on a plain "
                        f"white page"
                    )

                findings.append({
                    "page": page_number,
                    "text": span_text.strip()[:300],
                    "font": safe_string(span.get("font")),
                    "size_pt": round(size, 2),
                    "color_rgb": list(rgb),
                    "reasons": reasons,
                    "severity": (
                        "high"
                        if (is_tiny or is_near_white)
                        else "medium"
                    )
                })

    return findings


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

        "metadata_forensics": {},

        "reputation": {},

        "structure": {},

        "risky_words": [],

        "suspicious_paragraphs": [],

        "urls": [],

        "clickable_links": [],

        "images": [],

        "qr_codes": [],

        "hidden_text": [],

        "attachments": [],

        "suspicious_features": [],

        "javascript": [],

        "pages": [],

        "summary": {
            "status": "Low Risk",
            "indicator_score": 0,
            "total_risky_words": 0,
            "total_suspicious_paragraphs": 0,
            "total_urls": 0,
            "total_images": 0,
            "total_qr_codes": 0,
            "total_qr_urls": 0,
            "total_hidden_text_spans": 0,
            "hidden_text_high_severity_detected": False,
            "total_attachments": 0,
            "total_features": 0,
            "total_javascript_objects": 0,
            "total_suspicious_js_calls": 0,
            "javascript_cve_trigger_detected": False,
            "total_structural_anomalies": 0,
            "structural_high_severity_detected": False,

            "total_metadata_anomalies": 0,
            "metadata_high_severity_detected": False
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
        # METADATA FORENSICS
        # ====================================================
        # Producer/Creator signature matching against known
        # scripted/phishing-kit PDF generators, plus CreationDate vs.
        # ModDate anomaly detection -- see metadata_forensics.py
        # header comment. Runs off the /Info dict already read above,
        # so it has no other dependency.

        result["metadata_forensics"] = (
            metadata_forensics.analyze_metadata(metadata)
        )

        # ====================================================
        # PDF FEATURES
        # ====================================================

        result["suspicious_features"] = (
            detect_pdf_features(pdf_bytes)
        )

        # ====================================================
        # JAVASCRIPT EXTRACTION
        # ====================================================
        # Real extraction of script source (not just a "/JavaScript"
        # byte-string presence flag) -- see extract_javascript()
        # docstring. Needs the open pymupdf Document, so this has to
        # run after doc.open() but has no other dependency on the
        # page-loop state below.

        result["javascript"] = extract_javascript(doc)

        # ====================================================
        # VIRUSTOTAL FILE-HASH REPUTATION
        # ====================================================
        # Lookup only (no upload of unseen files -- see
        # virustotal_file.py header comment). Runs before the page
        # loop since it doesn't depend on anything extracted below,
        # and a slow/failed network call here still leaves every
        # other (local, offline) check in this function unaffected.

        result["reputation"] = virustotal_file.check_file(pdf_bytes)

        # ====================================================
        # STRUCTURAL / OBJECT ANOMALIES
        # ====================================================
        # Object-graph and raw-byte level checks (incremental-update
        # tampering, duplicate object definitions, page-count
        # mismatches, streams that don't decode cleanly) -- see
        # structure_checks.py header comment. Needs both the raw
        # bytes and the open Document, and doesn't depend on anything
        # extracted in the page loop below.

        result["structure"] = structure_checks.analyze_structure(
            pdf_bytes,
            doc
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
            # HIDDEN TEXT (TINY FONT / WHITE-ON-WHITE)
            # ------------------------------------------------
            # Same page object as the get_text("text") call above --
            # this just re-reads it in "dict" mode for per-span
            # size/color, so it stays cheap and doesn't need its own
            # try/except wrapper around the page (detect_hidden_text
            # already swallows its own extraction errors).

            hidden_text_matches = detect_hidden_text(
                page,
                page_number
            )

            result["hidden_text"].extend(
                hidden_text_matches
            )

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

                    # ------------------------------------------
                    # QR / BARCODE DECODING
                    # ------------------------------------------
                    # Run on the raw decoded image bytes (not the
                    # data-URI string) -- decode_qr_codes_from_image()
                    # needs an actual image to open with Pillow.

                    qr_hits = decode_qr_codes_from_image(
                        image_bytes
                    )

                    image_has_qr_url = False

                    for qr_hit in qr_hits:

                        qr_payload = qr_hit["data"]

                        qr_urls = extract_urls_from_text(
                            qr_payload
                        )

                        # A QR code often encodes a bare domain/path
                        # with no http(s)/www prefix (e.g.
                        # "bit.ly/x7Qz9") which extract_urls_from_text
                        # won't match on its own scheme-based pattern.
                        # If nothing matched but the payload still
                        # looks like a single URL-shaped token, treat
                        # the whole payload as one.
                        if (
                            not qr_urls
                            and " " not in qr_payload
                            and "." in qr_payload
                            and len(qr_payload) <= 500
                        ):
                            qr_urls = [qr_payload]

                        if qr_urls:
                            image_has_qr_url = True

                        result["qr_codes"].append({
                            "image_id": image_counter,
                            "page": page_number,
                            "barcode_type": qr_hit["type"],
                            "data": qr_payload[:500],
                            "urls": qr_urls
                        })

                        for qr_url in qr_urls:

                            normalized_qr_url = (
                                qr_url.lower()
                            )

                            if normalized_qr_url in found_urls:
                                continue

                            found_urls.add(
                                normalized_qr_url
                            )

                            result["urls"].append({
                                "url": qr_url,
                                "domain": get_domain(qr_url),
                                "page": page_number,
                                "source": (
                                    "QR code in embedded image"
                                )
                            })

                    result["images"].append({
                        "id": image_counter,
                        "page": page_number,
                        "width": width,
                        "height": height,
                        "format": image_extension,
                        "data": image_data,
                        "contains_qr_code": bool(qr_hits),
                        "qr_code_has_url": image_has_qr_url
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

        qr_code_count = len(
            result["qr_codes"]
        )

        qr_url_count = sum(
            len(qr.get("urls", []))
            for qr in result["qr_codes"]
        )

        hidden_text_count = len(
            result["hidden_text"]
        )

        hidden_text_high_severity_detected = any(
            item.get("severity") == "high"
            for item in result["hidden_text"]
        )

        javascript_object_count = len(
            result["javascript"]
        )

        suspicious_js_call_count = sum(
            len(script.get("suspicious_calls", []))
            for script in result["javascript"]
        )

        javascript_cve_trigger_detected = any(
            call.get("known_cve_trigger")
            for script in result["javascript"]
            for call in script.get("suspicious_calls", [])
        )

        # VirusTotal engines that flagged this exact file, if VT has
        # seen it before ("not_seen_before" or a skipped/error lookup
        # both correctly contribute 0 here -- see scoring note below).
        vt_malicious_count = (
            result["reputation"].get("malicious_count", 0) or 0
        )

        structural_anomalies = (
            result["structure"].get("anomalies", []) or []
        )

        structural_anomaly_count = len(structural_anomalies)

        structural_high_severity_detected = any(
            anomaly.get("severity") == "high"
            for anomaly in structural_anomalies
        )

        metadata_anomalies = (
            result["metadata_forensics"].get("anomalies", []) or []
        )

        metadata_anomaly_count = len(metadata_anomalies)

        metadata_high_severity_detected = any(
            anomaly.get("severity") == "high"
            for anomaly in metadata_anomalies
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

        # Embedded JavaScript. Presence alone is only a mild signal --
        # PDFs legitimately use JS for form-field math, print dialogs,
        # etc -- but a suspicious/exploit-associated API call inside
        # that JS is a much stronger one, so it's weighted separately
        # and higher.
        if javascript_object_count > 0:
            raw_score += 2

        raw_score += min(
            suspicious_js_call_count * 3,
            10
        )

        # VirusTotal file reputation. Weighted heavily on purpose --
        # an unrelated AV vendor's engines actually detonating/
        # signature-matching this exact file is stronger evidence
        # than any of the local heuristics above.
        raw_score += min(
            vt_malicious_count * 3,
            10
        )

        # QR codes that decode to a URL. This is a deliberate evasion
        # technique -- the link never appears as text or a /URI
        # action, only as pixels a text-based scanner can't read --
        # so it's weighted on par with a suspicious PDF feature
        # rather than treated as an ordinary extra URL.
        raw_score += min(
            qr_url_count * 3,
            10
        )

        # Structural/object anomalies (incremental-update tampering,
        # duplicate object definitions, page-count mismatches,
        # streams that fail to decode). Each one already represents a
        # fairly deliberate, unusual condition rather than incidental
        # noise, so it's weighted similarly to an embedded attachment.
        raw_score += min(
            structural_anomaly_count * 3,
            10
        )

        # Hidden text (tiny font and/or white-on-white). A couple of
        # stray tiny spans can happen in legitimately generated PDFs
        # (e.g. layout artifacts, kerning hacks), so this is weighted
        # like an ordinary suspicious-feature hit rather than as
        # heavily as a confirmed AV/CVE signal -- but it still adds
        # up quickly if a block of keyword-stuffed text is present.
        raw_score += min(
            hidden_text_count * 2,
            8
        )

        # Metadata forensics: a known scripted/phishing-kit generator
        # signature in Producer/Creator is a soft signal on its own
        # (plenty of legitimate systems use the same libraries), so
        # it's weighted lightly -- but a ModDate/CreationDate
        # inversion or future-dated timestamp is direct evidence the
        # /Info dictionary was hand-set rather than produced by a
        # normal save/export pipeline, which is why a high-severity
        # hit here also forces the verdict below, the same as a
        # structural anomaly does.
        raw_score += min(
            metadata_anomaly_count * 2,
            8
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

        # A file that VirusTotal engines already flag as malicious is
        # High Risk regardless of what the local heuristic score came
        # out to -- a confirmed AV hit shouldn't be diluted down to
        # "Medium" just because this particular PDF happens to have
        # few risky phrases or embedded features.
        if vt_malicious_count > 0:
            status = "High Risk"

        # Same logic for a documented exploit-trigger JS call
        # (e.g. Collab.getIcon) -- that's not a heuristic, it's a
        # named CVE trigger pattern, so it overrides the score-based
        # verdict the same way a confirmed AV hit does.
        if javascript_cve_trigger_detected:
            status = "High Risk"

        # Same logic again for a high-severity structural anomaly
        # (e.g. a declared-vs-actual page count mismatch) -- that's
        # direct evidence the file was hand-tampered after being
        # generated, not just a heuristic score contributor.
        if structural_high_severity_detected:
            status = "High Risk"

        # Same logic again for a high-severity metadata anomaly (a
        # ModDate that predates CreationDate, or a future-dated
        # timestamp) -- direct evidence the /Info dictionary was
        # hand-tampered, not just a heuristic score contributor.
        if metadata_high_severity_detected:
            status = "High Risk"

        result["summary"] = {
            "status": status,

            "indicator_score": indicator_score,

            "total_risky_words": risky_word_count,

            "total_suspicious_paragraphs":
                suspicious_section_count,

            "total_urls": url_count,

            "total_images": image_count,

            "total_qr_codes": qr_code_count,

            "total_qr_urls": qr_url_count,

            "total_hidden_text_spans": hidden_text_count,

            "hidden_text_high_severity_detected":
                hidden_text_high_severity_detected,

            "total_attachments": attachment_count,

            "total_features": feature_count,

            "total_javascript_objects": javascript_object_count,

            "total_suspicious_js_calls": suspicious_js_call_count,

            "javascript_cve_trigger_detected":
                javascript_cve_trigger_detected,

            "virustotal_malicious_engines": vt_malicious_count,

            "total_structural_anomalies": structural_anomaly_count,

            "structural_high_severity_detected":
                structural_high_severity_detected,

            "total_metadata_anomalies": metadata_anomaly_count,

            "metadata_high_severity_detected":
                metadata_high_severity_detected
        }

        return result

    finally:

        if doc is not None:

            try:
                doc.close()

            except Exception:
                pass
