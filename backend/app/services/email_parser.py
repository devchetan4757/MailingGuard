from email import policy
from email.parser import BytesParser
from email.header import decode_header, make_header


def decode_mime_header(value):
    """Decode an email header into a normal readable string."""
    if not value:
        return None

    try:
        return str(make_header(decode_header(value)))
    except (TypeError, ValueError):
        return str(value)


def parse_email(file_path):
    """
    Parse an .eml file and return its structured contents.

    The original .eml file is only read; this function does not
    permanently store or modify it.
    """
    with open(file_path, "rb") as email_file:
        message = BytesParser(policy=policy.default).parse(email_file)

    metadata = {
        "from": decode_mime_header(message.get("From")),
        "to": decode_mime_header(message.get("To")),
        "cc": decode_mime_header(message.get("Cc")),
        "bcc": decode_mime_header(message.get("Bcc")),
        "subject": decode_mime_header(message.get("Subject")),
        "date": decode_mime_header(message.get("Date")),
        "reply_to": decode_mime_header(message.get("Reply-To")),
        "message_id": decode_mime_header(message.get("Message-ID")),
        "return_path": decode_mime_header(message.get("Return-Path")),
        "authentication_results": decode_mime_header(
            message.get("Authentication-Results")
        ),
        "received_spf": decode_mime_header(message.get("Received-SPF")),
        "dkim_signature": decode_mime_header(message.get("DKIM-Signature")),
        "x_mailer": decode_mime_header(message.get("X-Mailer")),
        "x_originating_ip": decode_mime_header(message.get("X-Originating-IP")),
    }

    text_body = None
    html_body = None
    attachments = []

    if message.is_multipart():
        for part in message.walk():
            if part.is_multipart():
                continue

            content_type = part.get_content_type()
            disposition = part.get_content_disposition()
            filename = part.get_filename()

            if disposition == "attachment" or filename:
                payload = part.get_payload(decode=True) or b""

                attachments.append(
                    {
                        "filename": decode_mime_header(filename),
                        "content_type": content_type,
                        "size": len(payload),
                    }
                )
                continue

            if content_type == "text/plain" and text_body is None:
                text_body = part.get_content()

            elif content_type == "text/html" and html_body is None:
                html_body = part.get_content()

    else:
        content_type = message.get_content_type()

        if content_type == "text/plain":
            text_body = message.get_content()

        elif content_type == "text/html":
            html_body = message.get_content()

    return {
        "metadata": metadata,
        "body": {
            "text": text_body,
            "html": html_body,
        },
        "attachments": attachments,
    }