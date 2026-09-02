# analyzer_cli.py
#
# Thin CLI wrapper around analyze_pdf() so the dispatcher can run
# PDF analysis in an isolated subprocess. Reads a file path, prints
# the result dict as JSON to stdout.
#
# Usage: python analyzer_cli.py /path/to/file.pdf

import sys
import json

from analyzer import analyze_pdf


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: analyzer_cli.py <pdf_path>"}))
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()
    except Exception as error:
        print(json.dumps({"error": f"Could not read file: {error}"}))
        sys.exit(1)

    result = analyze_pdf(pdf_bytes, filename=file_path)
    print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
