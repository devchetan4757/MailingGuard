"""
MailGuard upload utilities.

Handles temporary storage of uploaded email files.

The analyzer works with a filesystem path, while FastAPI receives uploaded
files as bytes. This module bridges those two interfaces safely.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import BinaryIO


MAX_EMAIL_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = {
    ".eml",
}


class UploadValidationError(ValueError):
    """Raised when an uploaded email fails validation."""


def validate_filename(
    filename: str | None,
) -> str:
    """
    Validate and normalize the uploaded filename.
    """

    if not filename:
        raise UploadValidationError(
            "No email filename was provided."
        )

    safe_name = Path(
        filename
    ).name

    if not safe_name:
        raise UploadValidationError(
            "Invalid email filename."
        )

    extension = Path(
        safe_name
    ).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise UploadValidationError(
            "Only .eml email files are supported."
        )

    return safe_name


def validate_content(
    content: bytes,
) -> None:
    """
    Validate uploaded email content.
    """

    if not content:
        raise UploadValidationError(
            "The uploaded email file is empty."
        )

    if len(content) > MAX_EMAIL_SIZE:
        raise UploadValidationError(
            "The uploaded email exceeds the 10 MB limit."
        )


def save_temporary_email(
    content: bytes,
) -> str:
    """
    Save email bytes to a temporary .eml file.

    Returns:
        Absolute filesystem path to the temporary file.

    The caller is responsible for deleting the returned file.
    """

    validate_content(content)

    temporary_file = tempfile.NamedTemporaryFile(
        mode="wb",
        suffix=".eml",
        prefix="mailguard_",
        delete=False,
    )

    try:
        temporary_file.write(content)
        temporary_file.flush()

        return os.path.abspath(
            temporary_file.name
        )

    finally:
        temporary_file.close()


def save_upload_to_temp(
    upload: BinaryIO,
) -> str:
    """
    Save a file-like upload object to a temporary .eml file.
    """

    content = upload.read()

    if not isinstance(
        content,
        bytes,
    ):
        raise UploadValidationError(
            "Unable to read uploaded email."
        )

    return save_temporary_email(
        content
    )


def delete_temporary_email(
    file_path: str | None,
) -> None:
    """
    Remove a temporary MailGuard email file safely.
    """

    if not file_path:
        return

    try:
        path = Path(
            file_path
        )

        if path.exists():
            path.unlink()

    except OSError:
        # Cleanup failure should never hide the original analysis result.
        pass
