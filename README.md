# MailGuard

Email security analysis platform. Upload a suspicious `.eml`, get an instant
risk breakdown, then drill into links, sender domains, and attachments with
sandboxed AI-assisted deep analysis, all backed by a tamper-evident audit
trail.

## Why

Phishing emails hide behind faked headers, throwaway domains, and malicious
attachments that most triage tools either can't safely open or don't bother
inspecting closely. MailGuard parses the raw email, reconstructs its real
delivery path, and lets an analyst choose exactly what to deep-scan (a
link, the sender's domain, a PDF, or an image) without risking the host
system, and without scanning everything blindly.

## Features

- **Dashboard**: risk trends, alert queue, headline stats at a glance.
- **Email parsing**: structured breakdown of headers, body, and attachments
  from a raw `.eml`.
- **Origin trace map**: visualizes the actual `Received` header hop chain
  with geolocation, exposing spoofed "From" claims.
- **AI Deep Analysis** (on demand, per item):
  - **Link**: isolated crawl of a URL, checked for phishing patterns.
  - **Sender domain**: WHOIS age, registrar reputation, blacklist checks.
  - **PDF attachment**: parsed and inspected in a sandboxed subprocess.
  - **Image attachment**: EXIF/metadata extraction via `exiftool`.
  - Each analyzer's raw output can be summarized into plain language by
    Groq (optional, falls back to raw results if unconfigured).
- **Gmail integration**: pull an email directly from Gmail for analysis.
- **History & reporting**: hash-chained case history with exportable PDF
  reports.

## Tech stack

| Layer    | Stack |
|----------|-------|
| Frontend | React 18, Vite, React Router, Tailwind CSS, Recharts |
| Backend  | FastAPI (Python), Uvicorn |
| Analyzers| `requests` + BeautifulSoup (crawler), PyMuPDF (PDF), `exiftool` (image), `python-whois`/`dnspython` (domain) |
| AI       | Groq (`openai/gpt-oss-120b` by default) for result summarization |

## Project structure

```
backend/
  app/
    main.py              # FastAPI app + route registration
    core/                 # config, security
    api/                  # analyze, cases, report, origin, deep_analysis, gmail
    services/              # email parsing, scoring, hashchain, pdf export, etc.
    ai_analyzers/
      crawler/             # link analysis
      whois/                # domain/WHOIS analysis
      pdf_analyzer/         # PDF attachment analysis
      image-analyzer/       # image attachment (EXIF) analysis
  run.py                  # dev entrypoint
frontend/
  src/
    components/            # dashboard, results, gmail, etc.
    pages/, hooks/, api/, router/, context/
```

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- `exiftool` binary installed system-wide (required for image analysis):
  ```bash
  apt-get install libimage-exiftool-perl
  ```

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
FRONTEND_ORIGIN=http://localhost:5173
GROQ_API_KEY=your_groq_key_here        # optional, enables plain-language explanations
GROQ_MODEL=openai/gpt-oss-120b         # optional
GOOGLE_CLIENT_ID=                       # optional, enables Gmail integration
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/integrations/gmail/callback
```

Run the API:

```bash
uvicorn app.main:app --reload
# or: python run.py
```

API available at `http://localhost:8000` (docs at `/docs`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App available at `http://localhost:5173`.

## API overview

All routes are prefixed `/api`.

| Router | Purpose |
|--------|---------|
| `/api/analyze` | Core email analysis / scoring |
| `/api/cases` | Case history |
| `/api/report` | PDF report export |
| `/api/origin` | Header trace / origin intelligence |
| `/api/deep-analysis` | AI deep analysis: link, domain, PDF, image |
| `/api/integrations/gmail` | Gmail OAuth + fetch |

Health checks: `GET /health`, `GET /api/health`.

## Notes

- Max upload size is capped at 2MB (`MAX_UPLOAD_BYTES` in `core/config.py`).
- Each deep-analysis type runs as an isolated, time-boxed subprocess, so a
  malformed or malicious attachment can't crash or hang the main API
  process.
- If `GROQ_API_KEY` is unset, deep-analysis endpoints still return raw
  analyzer output, they just skip the human-readable explanation field.
- If image analysis fails with `Can't locate Image/ExifTool.pm`, your
  `exiftool` binary and its Perl module are on mismatched Perl versions,
  set `PERL5LIB` to the module's actual install path.
