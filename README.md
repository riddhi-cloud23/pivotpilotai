# PivotPilot AI

PivotPilot AI is a career-transition coach with a single-page web app and a FastAPI backend. It includes a realistic local demo, resume and job-description analysis, adaptive diagnostics, a feasible learning planner, portfolio and challenge workflows, mock interviews, an application tracker, and an on-demand career report.

## Run locally

Requirements: Python 3.11 or newer.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn backend.app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The API documentation is at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). The app serves from the same origin and uses deterministic demo fallbacks when Gemini or other services are not configured. The browser-only `index.html` demo also works without the backend, but PDF/DOCX parsing, model-assisted feedback, and server-side features require FastAPI.

## Publish the interactive demo on GitHub Pages

The included GitHub Actions workflow deploys `index.html` as a static demo on pushes to `main`. In the repository settings, enable **Pages → Build and deployment → GitHub Actions**. After the first successful workflow, the site is available at [https://riddhi-cloud23.github.io/pivotpilotai/](https://riddhi-cloud23.github.io/pivotpilotai/).

GitHub Pages does not run FastAPI. Resume PDF/DOCX parsing, Gemini-assisted output, and server-side analysis need a separately hosted API; configure `window.PIVOTPILOT_API_URL` with that API's URL and allow the Pages origin in `FRONTEND_ORIGINS`. The frontend-only demo remains usable with local fallbacks. For Supabase sign-in, add the Pages site URL to Supabase's allowed redirect URLs.

## Optional services

- **Supabase Auth and cloud workspace sync:** Set `SUPABASE_URL` and `SUPABASE_ANON_KEY` in the server `.env`, then connect the project's URL and public publishable/anon key on the app's Account page. Run [`supabase/schema.sql`](./supabase/schema.sql) in the Supabase SQL editor. Never put a service-role key in the browser.
- **Gemini structured generation:** Set `GEMINI_API_KEY` in the server `.env`. Without it, endpoints use transparent deterministic fallbacks.
- **PostgreSQL:** Set `DATABASE_URL` to a SQLAlchemy PostgreSQL URL. SQLite is the local default.
- **Frontend on another origin:** Set `FRONTEND_ORIGINS` to a comma-separated list of exact trusted origins and set `window.PIVOTPILOT_API_URL` before the app script loads.

`DEMO_MODE=true` allows anonymous demo API calls. Set it to `false` in a deployed environment and configure Supabase token verification. Keep `.env` private.

## Feature boundaries

Compensation ranges, readiness scores, percentile curves, and demo opportunities are directional or synthetic—not verified market surveys, hiring predictions, or live job listings. The public-project scanner inspects allowed public metadata/manifests only; it does not execute code or perform a security audit. The career agent generates reports on demand and never submits applications or contacts employers. Review AI-generated content and verify every resume claim before using it.

## Tests

```powershell
python -m compileall -q backend tests
python -m pytest -q
```
