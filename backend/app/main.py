import os
import tempfile

from flask import Flask, jsonify, request

from app.services.email_parser import parse_email


app = Flask(__name__)


@app.get("/")
def root():
    return {
        "project": "MailingGuard",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/api/parse-email")
def parse_uploaded_email():
    if "file" not in request.files:
        return jsonify({
            "error": "No file provided"
        }), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:
        return jsonify({
            "error": "No file selected"
        }), 400

    if not uploaded_file.filename.lower().endswith(".eml"):
        return jsonify({
            "error": "Only .eml files are supported"
        }), 400

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".eml",
            delete=False
        ) as temp_file:
            uploaded_file.save(temp_file)
            temp_path = temp_file.name

        parsed_email = parse_email(temp_path)

        return jsonify({
            "status": "success",
            "email": parsed_email
        })

    except Exception:
        return jsonify({
            "error": "Unable to parse email file"
        }), 400

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)