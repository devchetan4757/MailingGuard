# Ownership map

Read this before touching any file. It tells you exactly which folder is yours,
which files you edit, and which files are frozen (shared contracts — don't edit
these without telling the whole team, they will cause merge conflicts).

Rule of thumb: **you should only ever have changes inside your own row below.**
If you find yourself editing someone else's file, stop — either ask them to add
the hook you need, or add a TODO and flag it in the group chat.

## Backend

| Epic | Owner | Your folder | Files you edit | Frozen — don't touch |
|---|---|---|---|---|
| Epic 1 — Upload & parsing | _assign name_ | `backend/app/lib/eml_parser/`, `backend/app/services/parsing.py` | everything inside `lib/eml_parser/`, `services/parsing.py` | `app/models/schemas.py`, `app/api/analyze.py` |
| Epic 2 — AI risk scoring | _assign name_ | `backend/app/services/scoring.py` | `services/scoring.py` only | `app/models/schemas.py`, `app/api/analyze.py` |
| Epic 3 — Origin tracing & case memory | _assign name_ | `backend/app/services/similarity.py`, `backend/app/services/geolocation.py` | those two files only | `app/models/schemas.py`, `app/api/analyze.py`, `app/api/cases.py` |
| Epic 4 — Reporting & history | _assign name_ | `backend/app/services/pdf_export.py`, `backend/app/api/cases.py`, `backend/app/api/report.py` | those three files | `app/models/schemas.py` |
| Epic 5 — Security & integrity | _assign name_ | `backend/app/services/hashchain.py`, `backend/app/core/security.py` | those two files | everything else |
| Integrator / backend lead | _assign name_ | `backend/app/main.py`, `backend/app/api/__init__.py`, `backend/app/models/schemas.py`, `backend/app/core/config.py` | wires everyone's services together | — |

Every service file has a **frozen function signature** at the top (see the
`CONTRACT` comment in each file). You can rewrite the inside of the function
however you like — swap logic, add helper functions below it, import new
libraries — but do not change the function name, arguments, or return shape
without agreeing it with the integrator, because `api/analyze.py` calls it
exactly as declared.

## Frontend

| Epic | Owner | Your folder | Files you edit | Frozen — don't touch |
|---|---|---|---|---|
| Epic 1 — Upload & parsing | _assign name_ | `frontend/src/components/upload/`, `frontend/src/pages/UploadPage.jsx` | everything in `components/upload/`, `pages/UploadPage.jsx` | `api/client.js`, `router/index.jsx` |
| Epic 2 — AI risk scoring | _assign name_ | `frontend/src/components/results/RiskScoreCard.jsx`, `Badge.jsx`, `HeaderChecklist.jsx` | those three files | `pages/ResultsPage.jsx` layout |
| Epic 3 — Origin tracing & case memory | _assign name_ | `frontend/src/components/results/TraceMap.jsx`, `RelatedCasesPanel.jsx`, `RelatedCaseSummaryModal.jsx` | those three files | `pages/ResultsPage.jsx` layout |
| Epic 4 — Reporting & history | _assign name_ | `frontend/src/components/results/DownloadReportButton.jsx`, `frontend/src/components/history/`, `frontend/src/pages/HistoryPage.jsx` | those files | `router/index.jsx` |
| Integrator / frontend lead | _assign name_ | `frontend/src/pages/ResultsPage.jsx`, `router/index.jsx`, `api/`, `context/`, `components/layout/`, `styles/tokens.css` | assembles everyone's components into pages | — |

Every component has a **PROPS CONTRACT** comment block at the top listing
exactly what it receives and what it calls back. Build to that contract and
your component will drop into the page without the integrator needing to
touch your file.

## Why it's split this way

- One file per person per concern means two people are never editing the same
  file at the same time → no merge conflicts on save.
- `schemas.py` (backend) and the `api/` clients (frontend) are the **API
  contract** from the master doc — frozen so the frontend can build against
  mock data while the backend is still being wired up.
- Page files (`UploadPage.jsx`, `ResultsPage.jsx`, `HistoryPage.jsx`) mostly
  just import and arrange components — keep logic in the component files so
  the integrator's job on page files stays small.
