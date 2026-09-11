# structure_checks.py
#
# Structural / object-level anomaly detection for PDFs.
#
# These checks look at the raw byte stream and the object graph rather
# than rendered content. Phishing-kit "weaponizers" routinely produce
# their payload PDFs by patching a legitimate-looking template with an
# incremental update -- a second body + xref + trailer + %%EOF tacked
# onto the end of the file -- instead of rewriting it cleanly, or by
# duplicating/mismatching objects to swap in a malicious OpenAction,
# /URI target, or JS payload after the fact. None of that shows up in
# rendered page content, so it's invisible to a purely text/JS-based
# scan -- but it leaves a fingerprint in the file's low-level structure
# that a normal PDF-authoring tool (Word "Save as PDF", a scanner, a
# mail-merge system) essentially never produces on its own.
#
# Every check here is a heuristic, not proof of malice on its own --
# see the per-anomaly comments for the legitimate cases that can also
# trigger them. They're meant to be folded into the overall indicator
# score alongside the content-based checks elsewhere in this analyzer,
# not treated as a standalone verdict.

import re

EOF_MARKER = re.compile(rb'%%EOF')
OBJ_DEF = re.compile(rb'(\d+)\s+(\d+)\s+obj\b')

# Heuristic threshold, not a hard rule -- a PDF with a large form,
# many annotations, or embedded fonts legitimately has a higher
# objects-per-page count. This is one signal among several.
HIGH_OBJECTS_PER_PAGE = 40


def count_eof_markers(pdf_bytes):
    return len(EOF_MARKER.findall(pdf_bytes))


def find_duplicate_object_ids(pdf_bytes):
    """
    Walk every "<num> <gen> obj" definition in the raw byte stream,
    across all incremental-update bodies (a single pymupdf-resolved
    Document only ever exposes the *final* version of each object, so
    this has to run on the raw bytes to see earlier, overridden
    definitions).

    A cleanly-generated PDF defines each object number exactly once.
    A PDF that has been incrementally patched -- which is how most
    phishing-kit weaponizers add a payload to an otherwise clean
    template -- defines the *same* object number a second time later
    in the file, with the later definition silently winning. That's
    exactly the mechanism used to swap out an /OpenAction, /URI
    target, or /JS entry without touching anything a human sees when
    the file is opened in a normal viewer or previewed by a scanner.
    """

    seen_generation = {}
    duplicate_generations = {}

    for match in OBJ_DEF.finditer(pdf_bytes):

        obj_num = int(match.group(1))
        gen_num = int(match.group(2))

        if obj_num not in seen_generation:
            seen_generation[obj_num] = {gen_num}
            continue

        if gen_num not in seen_generation[obj_num]:
            seen_generation[obj_num].add(gen_num)

        duplicate_generations[obj_num] = seen_generation[obj_num]

    return {
        obj_num: sorted(gens)
        for obj_num, gens in duplicate_generations.items()
    }


def find_undecodable_streams(doc):
    """
    Ask MuPDF to decompress every stream object's declared filter(s)
    (FlateDecode, ASCII85Decode, etc). A stream that declares a filter
    but fails to decode cleanly is either simple corruption or -- more
    relevant here -- a stream whose /Filter or /Length was
    deliberately mismatched to break naive/static parsers while a
    more permissive renderer (Adobe Reader, a browser's PDF viewer)
    still recovers and displays it.
    """

    undecodable = []

    try:
        xref_count = doc.xref_length()
    except Exception:
        return undecodable

    for xref in range(1, xref_count):

        try:
            is_stream = doc.xref_is_stream(xref)
        except Exception:
            continue

        if not is_stream:
            continue

        try:
            doc.xref_stream(xref)
        except Exception as error:

            undecodable.append({
                "xref": xref,
                "error": str(error)[:200]
            })

    return undecodable


def get_declared_page_count(doc):
    """
    Read the /Count entry declared on the root /Pages node directly
    out of the object graph (as opposed to len(doc), which is the
    number of pages MuPDF actually traversed while building the
    document). These two numbers are supposed to always agree; a
    mismatch means the page tree was hand-edited after the file was
    generated (pages spliced in/out without updating the declared
    count), which normal PDF-generation tools don't produce.

    Returns None if the value can't be determined, so callers can
    distinguish "checked and it matched" from "couldn't check".
    """

    try:
        catalog_xref = doc.pdf_catalog()

        if not catalog_xref:
            return None

        key_type, key_value = doc.xref_get_key(catalog_xref, "Pages")

        if key_type != "xref" or not key_value:
            return None

        pages_xref = int(key_value.split()[0])

        count_type, count_value = doc.xref_get_key(pages_xref, "Count")

        if count_type != "int" or count_value in (None, ""):
            return None

        return int(count_value)

    except Exception:
        return None


def analyze_structure(pdf_bytes, doc):
    """
    Run every structural/object-level anomaly check and return a
    result dict, including a flat "anomalies" list the caller can fold
    into the overall indicator score and, for high-severity findings,
    into a forced verdict override -- the same pattern already used
    for a confirmed VirusTotal hit or a known CVE-trigger JS call.
    """

    anomalies = []

    # ---- page count: declared vs. actually traversed ----

    try:
        actual_page_count = len(doc)
    except Exception:
        actual_page_count = 0

    declared_page_count = get_declared_page_count(doc)

    page_count_mismatch = (
        declared_page_count is not None
        and declared_page_count != actual_page_count
    )

    if page_count_mismatch:

        anomalies.append({
            "type": "page_count_mismatch",
            "severity": "high",
            "description": (
                f"Root /Pages node declares {declared_page_count} "
                f"page(s) but {actual_page_count} were actually "
                f"found when the document was opened -- the page "
                f"tree was likely hand-edited after the file was "
                f"generated."
            )
        })

    # ---- object count vs. page count ----

    try:
        object_count = max(doc.xref_length() - 1, 0)
    except Exception:
        object_count = 0

    if actual_page_count > 0:
        objects_per_page = object_count / actual_page_count
    else:
        objects_per_page = float(object_count)

    object_count_anomaly = (
        (actual_page_count > 0 and objects_per_page > HIGH_OBJECTS_PER_PAGE)
        or (actual_page_count == 0 and object_count > 5)
    )

    if object_count_anomaly:

        anomalies.append({
            "type": "object_count_anomaly",
            "severity": "medium",
            "description": (
                f"{object_count} object(s) across only "
                f"{actual_page_count} page(s) "
                f"({objects_per_page:.1f} objects/page) -- unusually "
                f"dense for the visible content, consistent with "
                f"extra/hidden objects packed into the file."
            )
        })

    # ---- incremental updates (multiple %%EOF markers) ----

    eof_marker_count = count_eof_markers(pdf_bytes)
    incremental_update_detected = eof_marker_count > 1
    incremental_update_count = max(eof_marker_count - 1, 0)

    if incremental_update_detected:

        anomalies.append({
            "type": "incremental_update",
            "severity": "medium",
            "description": (
                f"File contains {eof_marker_count} '%%EOF' markers, "
                f"meaning {incremental_update_count} incremental "
                f"update(s) were appended after the file was first "
                f"saved. This is the standard technique used by PDF "
                f"phishing-kit 'weaponizers' to patch a malicious "
                f"action into an otherwise clean-looking template."
            )
        })

    # ---- duplicate object definitions ----

    duplicate_object_ids = find_duplicate_object_ids(pdf_bytes)

    if duplicate_object_ids:

        sample_obj = next(iter(duplicate_object_ids))
        sample_gens = duplicate_object_ids[sample_obj]

        severity = (
            "high" if incremental_update_detected else "medium"
        )

        anomalies.append({
            "type": "duplicate_object_ids",
            "severity": severity,
            "description": (
                f"{len(duplicate_object_ids)} object number(s) are "
                f"defined more than once in the file (e.g. object "
                f"{sample_obj} appears with generation(s) "
                f"{sample_gens}) -- the later definition silently "
                f"overrides the earlier one, which is how an "
                f"incremental update swaps out a link target or "
                f"action without changing anything a human sees."
            )
        })

    # ---- streams that don't decode cleanly ----

    undecodable_streams = find_undecodable_streams(doc)

    if undecodable_streams:

        xref_list = ", ".join(
            str(item["xref"]) for item in undecodable_streams[:10]
        )

        anomalies.append({
            "type": "undecodable_stream",
            "severity": "medium",
            "description": (
                f"{len(undecodable_streams)} stream object(s) "
                f"declare a filter but failed to decode cleanly "
                f"(xrefs: {xref_list}) -- consistent with a "
                f"deliberately mismatched /Filter or /Length used to "
                f"confuse parsers that don't recover as permissively "
                f"as a full PDF reader."
            )
        })

    return {
        "page_count_declared": declared_page_count,
        "page_count_actual": actual_page_count,
        "page_count_mismatch": page_count_mismatch,

        "object_count": object_count,
        "objects_per_page": round(objects_per_page, 2),
        "object_count_anomaly": object_count_anomaly,

        "eof_marker_count": eof_marker_count,
        "incremental_update_detected": incremental_update_detected,
        "incremental_update_count": incremental_update_count,

        "duplicate_object_count": len(duplicate_object_ids),
        "duplicate_object_ids": dict(
            list(duplicate_object_ids.items())[:25]
        ),

        "undecodable_stream_count": len(undecodable_streams),
        "undecodable_stream_xrefs": [
            item["xref"] for item in undecodable_streams[:25]
        ],

        "anomalies": anomalies
    }
