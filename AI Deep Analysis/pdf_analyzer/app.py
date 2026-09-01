# app.py

from flask import Flask, render_template, request, jsonify
from analyzer import analyze_pdf

app = Flask(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():

    if "file" not in request.files:
        return jsonify({
            "success": False,
            "error": "No PDF file was uploaded."
        }), 400

    uploaded_file = request.files["file"]

    if uploaded_file.filename == "":
        return jsonify({
            "success": False,
            "error": "No file selected."
        }), 400

    filename = uploaded_file.filename

    if not filename.lower().endswith(".pdf"):
        return jsonify({
            "success": False,
            "error": "Only PDF files are allowed."
        }), 400

    try:
        pdf_bytes = uploaded_file.read()

        if not pdf_bytes:
            return jsonify({
                "success": False,
                "error": "The uploaded file is empty."
            }), 400

        if not pdf_bytes.startswith(b"%PDF"):
            return jsonify({
                "success": False,
                "error": "The uploaded file does not appear to be a valid PDF."
            }), 400

        result = analyze_pdf(
            pdf_bytes=pdf_bytes,
            filename=filename
        )

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as error:
        print("\nPDF ANALYSIS ERROR")
        print("=" * 60)
        print(str(error))
        print("=" * 60)

        return jsonify({
            "success": False,
            "error": f"PDF analysis failed: {str(error)}"
        }), 500


@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "success": False,
        "error": "File is too large. Maximum allowed size is 50 MB."
    }), 413


if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("PDF THREAT ANALYZER SERVER")
    print("=" * 60)
    print("Open: http://127.0.0.1:5000")
    print("=" * 60 + "\n")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )