# ============================================================
# DEEP IMAGE ANALYZER - WINDOWS + EXIFTOOL
# ============================================================
#
# Folder structure:
#
# image-analyzer/
# ├── deep_image_analyzer.py
# ├── exiftool.exe
# ├── exiftool_files/
# └── test.jpg
#
# Run:
# python deep_image_analyzer.py test.jpg
#
# This script DOES NOT save any results.
# It only displays the analysis in the terminal.
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
    Find ExifTool.

    First checks:
    1. System PATH
    2. Same folder as this Python script
    """

    # Check if ExifTool is available in PATH
    exiftool_path = shutil.which("exiftool")

    if exiftool_path:
        return exiftool_path

    # Check for exiftool.exe beside this Python script
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
    """Run ExifTool and return all available metadata."""

    exiftool_path = get_exiftool_path()

    if exiftool_path is None:

        print("\n[ERROR] ExifTool was not found!")

        print("\nMake sure your folder looks like this:\n")

        print("image-analyzer/")
        print("│")
        print("├── deep_image_analyzer.py")
        print("├── exiftool.exe")
        print("├── exiftool_files/")
        print("└── test.jpg")

        return None

    print("\n[+] ExifTool found:")
    print(f"    {exiftool_path}")

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

        # ExifTool:
        # 0 = success
        # 1 = warning but data may still be returned

        if result.returncode not in [0, 1]:

            print("\n[EXIFTOOL ERROR]")

            if result.stderr:
                print(result.stderr)

            return None

        if not result.stdout.strip():

            print("\n[ERROR] ExifTool returned no metadata.")

            return None

        data = json.loads(result.stdout)

        if not data:
            return None

        return data[0]

    except FileNotFoundError:

        print("\n[ERROR] Could not execute exiftool.exe.")

        return None

    except json.JSONDecodeError:

        print("\n[ERROR] Could not parse ExifTool output.")

        return None

    except Exception as error:

        print(f"\n[ERROR] {error}")

        return None


# ============================================================
# PRINT SECTION
# ============================================================

def print_section(title):

    print("\n")
    print("=" * 75)
    print(f" {title}")
    print("=" * 75)


# ============================================================
# FIND METADATA
# ============================================================

def find_metadata(metadata, keywords):
    """Find metadata matching keywords."""

    results = {}

    for key, value in metadata.items():

        key_lower = key.lower()

        for keyword in keywords:

            if keyword.lower() in key_lower:

                results[key] = value
                break

    return results


# ============================================================
# PRINT METADATA GROUP
# ============================================================

def print_metadata_group(metadata, title, keywords):

    results = find_metadata(metadata, keywords)

    print_section(title)

    if results:

        for key, value in results.items():

            print(f"{key:<45}: {value}")

    else:

        print("No metadata found.")


# ============================================================
# PRIVACY ANALYSIS
# ============================================================

def analyze_privacy(metadata):

    print_section("PRIVACY & SECURITY ANALYSIS")

    findings = []

    for key, value in metadata.items():

        key_lower = key.lower()

        # GPS / Location information
        if any(word in key_lower for word in [
            "gpslatitude",
            "gpslongitude",
            "gpsposition",
            "gpsaltitude"
        ]):

            findings.append(
                f"[!] Location metadata found: {key} = {value}"
            )

        # Device serial numbers
        elif any(word in key_lower for word in [
            "serialnumber",
            "bodyserial"
        ]):

            findings.append(
                f"[!] Device information found: {key}"
            )

        # Editing software
        elif any(word in key_lower for word in [
            "software",
            "creatortool",
            "photoshop",
            "lightroom"
        ]):

            findings.append(
                f"[!] Software metadata found: {key} = {value}"
            )

    if findings:

        for finding in findings:
            print(finding)

    else:

        print("[+] No obvious sensitive metadata detected.")


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    print("\n")
    print("###########################################################")
    print("#                                                         #")
    print("#              DEEP IMAGE FORENSIC ANALYZER               #")
    print("#                                                         #")
    print("###########################################################")

    # --------------------------------------------------------
    # CHECK COMMAND
    # --------------------------------------------------------

    if len(sys.argv) != 2:

        print("\nUsage:")
        print("python deep_image_analyzer.py <image_file>")

        print("\nExample:")
        print("python deep_image_analyzer.py test.JPG")

        return

    # --------------------------------------------------------
    # GET FILE
    # --------------------------------------------------------

    file_path = Path(sys.argv[1]).resolve()

    if not file_path.exists():

        print("\n[ERROR] File not found:")
        print(file_path)

        return

    if not file_path.is_file():

        print("\n[ERROR] The provided path is not a file.")

        return

    # --------------------------------------------------------
    # FILE INFORMATION
    # --------------------------------------------------------

    print("\n[+] Target file:")
    print(f"    {file_path}")

    print("\n[+] File size:")
    print(f"    {file_path.stat().st_size:,} bytes")

    # --------------------------------------------------------
    # FILE HASHES
    # --------------------------------------------------------

    try:

        hashes = calculate_hashes(file_path)

        print_section("FILE HASHES")

        print(f"MD5    : {hashes['MD5']}")
        print(f"SHA256 : {hashes['SHA256']}")

    except Exception as error:

        print(f"\n[ERROR] Hash calculation failed: {error}")

    # --------------------------------------------------------
    # EXTRACT METADATA
    # --------------------------------------------------------

    print("\n[+] Extracting deep metadata...")

    metadata = run_exiftool(file_path)

    if metadata is None:

        print("\n[ERROR] Analysis could not continue.")

        return

    # --------------------------------------------------------
    # FILE INFORMATION
    # --------------------------------------------------------

    print_metadata_group(
        metadata,
        "FILE INFORMATION",
        [
            "filename",
            "directory",
            "filesize",
            "filetype",
            "filetypeextension",
            "mimetype",
            "imagewidth",
            "imageheight",
            "imagesize",
            "megapixels",
            "filemodifydate",
            "fileaccessdate",
            "filecreatedate"
        ]
    )

    # --------------------------------------------------------
    # CAMERA INFORMATION
    # --------------------------------------------------------

    print_metadata_group(
        metadata,
        "CAMERA & DEVICE INFORMATION",
        [
            "make",
            "model",
            "lens",
            "serialnumber",
            "bodyserial"
        ]
    )

    # --------------------------------------------------------
    # CAPTURE INFORMATION
    # --------------------------------------------------------

    print_metadata_group(
        metadata,
        "IMAGE CAPTURE INFORMATION",
        [
            "datetime",
            "createdate",
            "modifydate",
            "exposure",
            "iso",
            "aperture",
            "fnumber",
            "shutterspeed",
            "focallength",
            "flash",
            "whitebalance",
            "metering",
            "scene"
        ]
    )

    # --------------------------------------------------------
    # GPS INFORMATION
    # --------------------------------------------------------

    print_metadata_group(
        metadata,
        "GPS & LOCATION INFORMATION",
        [
            "gps",
            "latitude",
            "longitude",
            "altitude",
            "location",
            "city",
            "country",
            "state",
            "province"
        ]
    )

    # --------------------------------------------------------
    # SOFTWARE INFORMATION
    # --------------------------------------------------------

    print_metadata_group(
        metadata,
        "SOFTWARE & EDITING INFORMATION",
        [
            "software",
            "creatortool",
            "history",
            "editing",
            "photoshop",
            "lightroom"
        ]
    )

    # --------------------------------------------------------
    # COLOR / IMAGE PROFILE
    # --------------------------------------------------------

    print_metadata_group(
        metadata,
        "COLOR & IMAGE PROFILE",
        [
            "colorspace",
            "profile",
            "icc",
            "resolution",
            "orientation",
            "bitdepth",
            "bitsper"
        ]
    )

    # --------------------------------------------------------
    # XMP / IPTC
    # --------------------------------------------------------

    print_metadata_group(
        metadata,
        "XMP / IPTC INFORMATION",
        [
            "xmp",
            "iptc",
            "copyright",
            "artist",
            "creator",
            "author",
            "description",
            "keywords"
        ]
    )

    # --------------------------------------------------------
    # PRIVACY CHECK
    # --------------------------------------------------------

    analyze_privacy(metadata)

    # --------------------------------------------------------
    # COMPLETE METADATA
    # --------------------------------------------------------

    print_section("COMPLETE RAW METADATA")

    for key in sorted(metadata.keys()):

        print(f"{key:<45}: {metadata[key]}")

    # --------------------------------------------------------
    # FINISHED
    # --------------------------------------------------------

    print_section("ANALYSIS COMPLETE")

    print("[+] Analysis displayed successfully.")
    print("[+] No report or metadata file was saved.")
    print("[+] No changes were made to the original image.")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()