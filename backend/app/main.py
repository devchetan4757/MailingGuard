from flask import Flask

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