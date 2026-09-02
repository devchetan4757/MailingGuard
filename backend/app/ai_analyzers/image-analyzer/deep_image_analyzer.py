# ============================================================
# DEEP IMAGE ANALYZER - BACKEND VERSION
# ============================================================
#
# Requires ExifTool to be installed on the server and available
# on PATH (e.g. `apt-get install libimage-exiftool-perl` on
# Linux, `brew install exiftool` on macOS). The old exiftool.exe
# was Windows-only and shouldn't be shipped with the backend.
#
# `analyze_image()` returns a structured dict instead of printing,
# so the AI layer can consume it directly. A thin CLI wrapper is
# kept at the bottom for manual testing.
# ============================================================

import sys
import json
import shutil
import subprocess
import hashlib
from pathlib import Path


# ============================================================
# FIND EXIFTOOL
# ============================================================

def get_exiftool_path():
    """
    Find ExifTool on the system PATH.
    (Falls back to an exiftool.exe placed beside this script only
    if you're running locally on Windows without a PATH install.)
    """

    exiftool_path = shutil.which("exiftool")

    if exiftool_path:
        return exiftool_path

    script_folder = Path(__file__).resolve().parent
    local_exiftool = script_folder / "exiftool.exe"

    if local_exiftool.exists():
        return str(local_exiftool)

    return None


# ============================================================
# CALCULATE FILE HASHES
# ============================================================

def calculate_hashes(file_path):
    """Calculate MD5 and SHA256 hashes."""

    md5_hash = hashlib.md5()
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as file:

        while True:
            chunk = file.read(8192)

            if not chunk:
                break

            md5_hash.update(chunk)
            sha256_hash.update(chunk)

    return {
        "MD5": md5_hash.hexdigest(),
        "SHA256": sha256_hash.hexdigest()
    }


# ============================================================
# RUN EXIFTOOL
# ============================================================

def run_exiftool(file_path):
    """Run ExifTool and return (metadata_dict_or_None, error_str_or_None)."""

    exiftool_path = get_exiftool_path()

    if exiftool_path is None:
        return None, (
            "ExifTool was not found on PATH. Install it on the server "
            "(e.g. `apt-get install libimage-exiftool-perl`)."
        )

    command = [
        exiftool_path,
        "-json",
        "-G1",
        "-a",
        "-u",
        "-n",
        str(file_path)
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        # ExifTool: 0 = success, 1 = warning but data may still be returned
        if result.returncode not in [0, 1]:
            return None, result.stderr.strip() or "ExifTool returned an error."

        if not result.stdout.strip():
            return None, "ExifTool returned no metadata."

        data = json.loads(result.stdout)

        if not data:
            return None, "ExifTool returned no metadata."

        return data[0], None

    except FileNotFoundError:
        return None, "Could not execute exiftool."

    except json.JSONDecodeError:
        return None, "Could not parse ExifTool output."

    except Exception as error:
        return None, str(error)


# ============================================================
# FIND METADATA BY KEYWORD GROUP
# ============================================================

def find_metadata(metadata, keywords):
    """Find metadata entries whose key matches any of the given keywords."""

    results = {}

    for key, value in metadata.items():

        key_lower = key.lower()

        for keyword in keywords:

            if keyword.lower() in key_lower:
                results[key] = value
                break

    return results


METADATA_GROUPS = {
    "file_information": [
        "filename", "directory", "filesize", "filetype",
        "filetypeextension", "mimetype", "imagewidth", "imageheight",
        "imagesize", "megapixels", "filemodifydate", "fileaccessdate",
        "filecreatedate"
    ],
    "camera_device_information": [
        "make", "model", "lens", "serialnumber", "bodyserial"
    ],
    "capture_information": [
        "datetime", "createdate", "modifydate", "exposure", "iso",
        "aperture", "fnumber", "shutterspeed", "focallength", "flash",
        "whitebalance", "metering", "scene"
    ],
    "gps_location_information": [
        "gps", "latitude", "longitude", "altitude", "location",
        "city", "country", "state", "province"
    ],
    "software_editing_information": [
        "software", "creatortool", "history", "editing", "photoshop",
        "lightroom"
    ],
    "color_image_profile": [
        "colorspace", "profile", "icc", "resolution", "orientation",
        "bitdepth", "bitsper"
    ],
    "xmp_iptc_information": [
        "xmp", "iptc", "copyright", "artist", "creator", "author",
        "description", "keywords"
    ]
}


# ============================================================
# PRIVACY ANALYSIS
# ============================================================

def analyze_privacy(metadata):

    findings = []

    for key, value in metadata.items():

        key_lower = key.lower()

        if any(word in key_lower for word in [
            "gpslatitude", "gpslongitude", "gpsposition", "gpsaltitude"
        ]):
            findings.append({
                "type": "location",
                "field": key,
                "value": value,
                "message": f"Location metadata found: {key} = {value}"
            })

        elif any(word in key_lower for word in [
            "serialnumber", "bodyserial"
        ]):
            findings.append({
                "type": "device_serial",
                "field": key,
                "value": value,
                "message": f"Device information found: {key}"
            })

        elif any(word in key_lower for word in [
            "software", "creatortool", "photoshop", "lightroom"
        ]):
            findings.append({
                "type": "editing_software",
                "field": key,
                "value": value,
                "message": f"Software metadata found: {key} = {value}"
            })

    return findings


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def analyze_image(file_path):
    """
    Run a full forensic/metadata analysis on an image and return the
    result as a structured dict. This is the function the AI layer
    should import and call directly.
    """

    file_path = Path(file_path).resolve()

    result = {
        "file_path": str(file_path),
        "exists": file_path.exists(),
        "file_size_bytes": None,
        "hashes": None,
        "metadata_groups": {},
        "raw_metadata": None,
        "privacy_findings": [],
        "error": None
    }

    if not result["exists"]:
        result["error"] = "File not found."
        return result

    if not file_path.is_file():
        result["error"] = "The provided path is not a file."
        return result

    result["file_size_bytes"] = file_path.stat().st_size

    try:
        result["hashes"] = calculate_hashes(file_path)
    except Exception as error:
        result["error"] = f"Hash calculation failed: {error}"
        return result

    metadata, exiftool_error = run_exiftool(file_path)

    if metadata is None:
        result["error"] = exiftool_error
        return result

    result["raw_metadata"] = metadata

    for group_name, keywords in METADATA_GROUPS.items():
        result["metadata_groups"][group_name] = find_metadata(
            metadata,
            keywords
        )

    result["privacy_findings"] = analyze_privacy(metadata)

    return result


# ============================================================
# OPTIONAL CLI WRAPPER (manual testing only, not used by the AI layer)
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("\nUsage:")
        print("python deep_image_analyzer.py <image_file>")
        sys.exit(1)

    output = analyze_image(sys.argv[1])
    print(json.dumps(output, indent=2, default=str))
