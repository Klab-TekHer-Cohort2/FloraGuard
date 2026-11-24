# FloraGuard backend

This is the backend and prototype risk service for the FloraGuard rose-health PWA. It is a FastAPI application with SQLite storage, connected to the React app through its `src/api.js` client and optionally to the root AI predictor through `FLORAGUARD_PREDICTOR=predictor:predict_image`.

## What exists in the project

The project also includes a root-level AI/data pipeline. Its `predictor.py` exposes the backend callable, while model weights and real rose images must be supplied, reviewed, and activated separately. The frontend calls this backend for reports, map aggregates, and alerts; no synthetic fallback is used if the API is unavailable.

## Architecture

- `app/main.py` — FastAPI application, multipart validation, API routes, CORS, and uploaded-image serving.
- `app/database.py` — SQLite schema and repository operations for reports, weather observations, risk results, alerts, and IVR sessions.
- `app/predictor.py` — validated adapter for the optional root `predictor.py`.
- `app/weather.py` — Open-Meteo current weather client; missing coordinates or provider failures return unavailable values.
- `app/risk_engine.py` — transparent rule-based, shared area/proximity risk score.
- `app/services.py` — single report-processing path for photo reports and user observations; alert generation.
- `app/channels.py` — provider-independent USSD menu and IVR keypad workflows.
- `app/seed_demo.py` — opt-in synthetic sample data.
- `tests/` — API and integration tests using temporary SQLite databases and mocked external services.

### User-reported vs. AI-detected

| Channel | Problem source | `predicted_problem` | `reported_problem` | Confidence | Image |
|---|---|---|---|---|---|
| Smartphone | Member 1 model, when configured | AI output | `null` | Model output or `null` when unavailable | Required |
| USSD | User menu selection | `null` | User observation | Always `null` | Not available |
| IVR | User keypad selection | `null` | User observation | Always `null` | Not available |

Every response includes `input_channel`, `ai_status`, and `is_sample` so consumers can preserve these distinctions. A missing model is reported as `uncertain` with a null confidence; the backend does not invent a prediction.

## Run locally (Windows PowerShell)

Python 3.10+ is required.

```powershell
# Run from the FloraGuard project root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for interactive OpenAPI documentation and `http://127.0.0.1:8000/api/health` for service health.

The Uvicorn command is run from the project root so `predictor:predict_image` can be imported when enabled. To train or run the AI model, use Python 3.11 and install the separate root `requirements.txt`; see the root [`AI_INTEGRATION.md`](../AI_INTEGRATION.md). Do not enable the predictor until a model has been trained and activated.

The SQLite database and validated uploads are stored under `backend/data/` by default. These runtime files are ignored by Git.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `FLORAGUARD_DATABASE_PATH` | `backend/data/floraguard.db` | SQLite database path |
| `FLORAGUARD_UPLOAD_DIR` | `backend/data/uploads` | Uploaded images |
| `FLORAGUARD_AREAS` | `Gishari Flower Park` | Comma-separated allowed USSD/IVR areas |
| `FLORAGUARD_AREA_COORDINATES` | empty | Optional, operator-verified area centroids (`Area:lat,lon;Area2:lat,lon`) for area-only weather/map context |
| `FLORAGUARD_USSD_CODE` | `*XXX#` | Placeholder only; no real telecom code is assumed |
| `FLORAGUARD_CONFIDENCE_THRESHOLD` | `0.60` | Predictions below this value become `uncertain` |
| `FLORAGUARD_RISK_WINDOW_DAYS` | `7` | Recent-report window |
| `FLORAGUARD_RISK_RADIUS_KM` | `5` | Proximity threshold when GPS is available |
| `FLORAGUARD_RISK_MEDIUM_THRESHOLD` | `30` | Minimum score classified MEDIUM |
| `FLORAGUARD_RISK_HIGH_THRESHOLD` | `65` | Minimum score classified HIGH |
| `FLORAGUARD_MAX_IMAGE_SIZE_MB` | `10` | Upload limit |
| `FLORAGUARD_WEATHER_TIMEOUT_SECONDS` | `4` | Weather request timeout |
| `FLORAGUARD_PREDICTOR` | empty | Optional callable import path; after model activation, use `predictor:predict_image` |
| `FLORAGUARD_CORS_ORIGINS` | localhost Vite origins | Comma-separated allowed frontend origins |

Area coordinates must be supplied by the deployment team; none are guessed or bundled.

## Smartphone workflow

`POST /api/reports` accepts `multipart/form-data`:

```text
image: <JPEG, PNG, or WebP>
latitude: -1.9       (optional; supply with longitude)
longitude: 29.8      (optional; supply with latitude)
area: Gishari Flower Park  (optional; defaults to the first configured area)
timestamp: 2026-11-24T08:30:00Z  (optional ISO-8601)
```

The backend validates type, signature, and size; saves the image with a generated name; calls the predictor adapter; obtains weather when coordinates are available; evaluates recent same-area/nearby reports; stores the report and analysis; and creates an alert when the rule engine returns `HIGH`. Weather failure or missing model does not block storing the report.

Example response:

```json
{
  "id": 1,
  "input_channel": "SMARTPHONE",
  "image_url": "/uploads/...",
  "image_available": true,
  "ai_status": "unavailable",
  "predicted_problem": "uncertain",
  "reported_problem": null,
  "problem": "uncertain",
  "severity": "unknown",
  "confidence": null,
  "area": "Gishari Flower Park",
  "weather_status": "unavailable",
  "temperature": null,
  "humidity": null,
  "risk_level": "LOW",
  "risk_score": 0,
  "risk_reasons": ["No recent concentration of similar reports was found."],
  "alert_generated": false,
  "is_sample": false
}
```

Member 1 can expose a Python callable such as:

```python
def predict_image(image_path: str) -> dict:
    return {
        "problem": "spider_mite",
        "severity": "medium",
        "confidence": 0.87,
    }
```

Set `FLORAGUARD_PREDICTOR=your_package.your_module:predict_image`. Accepted problem values: `healthy`, `spider_mite`, `thrips`, `powdery_mildew`, `downy_mildew`, `grey_mould`, `black_spot`, `uncertain`. Severity values: `low`, `medium`, `high`, `unknown`. Confidence must be numeric from 0 to 1 or `null`. The adapter validates output and applies the configured confidence threshold. Invalid model output is logged and stored as uncertain, rather than fabricated.

## USSD workflow

`POST /api/ussd` accepts the provider's session id and cumulative menu text. The telecom adapter only needs to map its callback fields to this provider-independent shape:

```json
{"session_id":"provider-session-123","text":"1*1*2*1"}
```

Menu: `1` report; `2` check area risk; `3` latest alert; `4` help. A report selects problem, severity, then configured area. The response follows `CON ...` / `END ...` conventions. USSD entries use `reported_problem`, have `confidence: null`, and never invoke the vision model.

## IVR workflow

`POST /api/ivr` accepts one keypad event per call:

```json
{"session_id":"provider-call-123"}
{"session_id":"provider-call-123","digit":"1"}
```

The backend stores minimal call state in SQLite (no caller phone number). The provider adapter reads the returned prompt/state and plays it; each subsequent DTMF event is posted with the same session id. Users can file an observation or hear the latest alert/area risk. IVR observations use the same report service and risk engine as smartphone and USSD reports.

## Shared rule-based risk and alerts

The prototype risk engine combines recent same-problem report counts (18 points for 2, 30 for 3–4, 45 for 5+), reported severity (2/6/10 points by low/medium/high, capped at 20), proximity (10 points when several similar reports are within the configured radius), and problem/weather rules (15 points when conditions may favour the problem). Scores cap at 100; configurable thresholds classify `LOW`, `MEDIUM`, or `HIGH`. Reports without coordinates can contribute by exact configured area. A `HIGH` result creates an alert available to smartphone/API, USSD, and IVR callers. Alert guidance is general; the backend does not provide pesticide instructions.

These are transparent prototype heuristics, not scientifically validated outbreak predictions. Weather context comes from Open-Meteo's current conditions when location coordinates are available. If Open-Meteo is down, the report is still saved and weather fields remain `null` with `weather_status: "unavailable"`.

## API reference for Member 3

All routes are under `/api`. Interactive request/response schemas are available at `/docs`.

| Method and URL | Purpose | Request | Main response |
|---|---|---|---|
| `POST /api/reports` | Submit smartphone photo and run prediction/risk | Multipart `image` required; optional coordinates, area, timestamp | Stored report, AI/weather/risk fields, `alert_generated` |
| `GET /api/reports` | List reports | Optional `area`, `input_channel`, `limit` | Array of report records |
| `GET /api/reports/{id}` | Get one report | Integer id in path | One report or 404 |
| `GET /api/map/reports` | Coarse map aggregates | None | `{areas:[{area,latitude,longitude,risk_level,risk_score,problem,report_count}]}` |
| `GET /api/risk` | Recalculate area indicator | Optional `area`, `problem` query | Level, score, reasons, window, weather status, prototype notice |
| `GET /api/alerts` | List high-risk alerts | Optional `area`, `limit` | Alert array with guidance and delivery status |
| `POST /api/ussd` | Provider-independent USSD callback | `{"session_id":"...","text":"1*..."}` | `{"action":"continue/end","message":"CON/END ..."}` and report when submitted |
| `POST /api/ivr` | Provider-independent IVR/DTMF callback | `{"session_id":"...","digit":"1"}` | `{"action":"continue/end","state":"...","message":"..."}` |
| `GET /api/health` | Check API/database | None | API, database, AI availability, weather/risk mode |

Validation errors return 4xx JSON `detail`; storage failures return 500; database health failure returns 503. Invalid image MIME is 415, signature mismatch is 400, and oversize is 413. No credentials or telecom provider secrets are part of these APIs.

The map endpoint returns configured area aggregates only, with GPS centroids rounded to two decimal places. It omits report ids, farmer names, phone numbers, and exact farm coordinates.

## Sample data

Seed synthetic examples once:

```powershell
cd backend
python -m app.seed_demo
```

The generated areas are named `SAMPLE - ...`, every record has `is_sample: true`, and no farm identity, photo, coordinates, weather, or model confidence is fabricated. The seed includes low/medium/high cases and all three reporting channels. It is idempotent and will not add a second sample set when one already exists.

To include the synthetic areas in map results, set `FLORAGUARD_AREAS="SAMPLE - Low Risk,SAMPLE - Medium Risk,SAMPLE - High Risk"` in `backend/.env`; never relabel these records as actual Gishari observations.

## Tests

```powershell
cd backend
python -m pytest -q
```

The integration suite uses temporary SQLite databases and mocked model/weather dependencies; it does not call Open-Meteo or require Member 1's model.

## Graph RAG

Graph RAG is not implemented. It is intentionally deferred until the report, model, weather, shared-risk, channel, and alert flows are stable. Any future retrieval/LLM explanation must not determine or override the official rule-based risk level.

## Frontend connection

The existing Vite app's `src/api.js` still uses demo data and was not changed. Member 3 can use `http://localhost:8000/api` as the local backend base, configure CORS with the frontend origin, and map `risk_reasons`, `confidence`, `ai_status`, and `is_sample` explicitly. The current mock `submitReport(photo)` result shape is not the backend report contract; adapt at the integration boundary rather than treating USSD/IVR observations as AI diagnoses.
