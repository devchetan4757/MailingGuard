from fastapi import FastAPI

app = FastAPI(
    title="API",
    version="0.1.0"
)


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
