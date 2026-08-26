from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.security_routes import router as security_router

app = FastAPI(
    title="API",
    version="0.1.0"
)

# Allow the Vite dev server (frontend) to call this API during development.
# Tighten this list before deploying anywhere real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(security_router)


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
