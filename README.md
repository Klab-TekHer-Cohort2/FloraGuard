# FloraGuard

FloraGuard is a mobile-first rose-health project with a React PWA, a FastAPI reporting/risk backend, and an AI/data pipeline. Growers can submit rose photos and view community alerts; managers can review reports and area risk summaries. A trained model and reviewed dataset are not included. Without an active model, the backend reports an unknown diagnosis rather than inventing one. Severity and area risk indicators are prototypes, not expert-validated predictions.

## Quick start

Requires Node.js 18 or newer. The backend requires Python 3.10+; TensorFlow training/inference targets Python 3.11.

```sh
npm.cmd install
npm.cmd run dev
```

Run the frontend from the project root. Start the backend from a second terminal at the project root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
python -m uvicorn backend.app.main:app --reload --port 8000
```

Open the Vite URL printed in the first terminal. The API docs are at `http://127.0.0.1:8000/docs`. Build the frontend with `npm.cmd run build`. Backend tests: `python -m pytest -q backend\tests`.

## Backend and frontend

The FastAPI backend in [`backend/`](./backend/README.md) provides SQLite-backed reports, a predictor adapter, Open-Meteo weather lookup, one shared rule-based risk engine, alerts, and provider-independent USSD/IVR APIs. The frontend's `src/api.js` uses `http://127.0.0.1:8000/api` by default; override it with `VITE_API_BASE_URL` in the root `.env` file when needed.

## AI and data pipeline

The AI/data pipeline is integrated at the project root: `predictor.py` provides the backend-compatible `predict_image(path)` function; `dataset_tools.py`, `train_model.py`, `severity.py`, and `activate_model.py` cover dataset validation, training, prototype visual severity, and model selection. See the preserved [AI workspace guide](./AI_README.md) and follow [`AI_INTEGRATION.md`](./AI_INTEGRATION.md), [`DATASET.md`](./DATASET.md), and [`TRAINING.md`](./TRAINING.md) before configuring a model.

No rose photos, trained model weights, or evaluation results are included. The checked-in source manifest is empty. Install AI dependencies with `python -m pip install -r requirements.txt` in a Python 3.11 environment. After adding and reviewing real data, training, and activating a model, set `FLORAGUARD_PREDICTOR=predictor:predict_image` in `backend/.env` and run Uvicorn from the project root. Optionally select a model with `FLORAGUARD_MODEL_PATH`.

The cloned AI workspace also contains an optional Neo4j knowledge layer. It is not required by the app or the standard predictor; see [AI_ARCHITECTURE.md](./AI_ARCHITECTURE.md) and [knowledge_graph/README.md](./knowledge_graph/README.md) before installing `requirements-neo4j.txt`.

## Project structure

```text
src/
  components/       Shared controls, navigation, map, and feedback
  context/          Theme, role, and backend alert state
  hooks/            Offline, role, and alert hooks
  i18n/             English and Kinyarwanda dictionaries
  pages/            Grower and dashboard screens
backend/
  app/              FastAPI, SQLite, predictor adapter, weather, risk and channel services
  tests/            Backend API and risk tests
data/                Source manifest and labelled-image folders
models/              Activated/versioned model outputs (weights are not included)
notebooks/            Model training notebook
tests/                AI/data pipeline tests
predictor.py          Backend-compatible AI inference entry point
train_model.py        Training and evaluation workflow
dataset_tools.py      Dataset validation and split tools
requirements.txt      AI/data Python dependencies
```

## Design system

The interface uses Plus Jakarta Sans for headings and Inter for body text. Design tokens are CSS custom properties in `src/index.css`; the app supports light and dark themes. See [design-notes.md](./design-notes.md) for contrast checks, typography, spacing, motion, and privacy decisions.

## Languages

The language selector supports English (`src/i18n/en.json`) and Kinyarwanda (`src/i18n/rw.json`). To add a language:

1. Copy the nested key structure from `en.json` into a new locale JSON file.
2. Translate every user-facing string and add the locale to `src/i18n/useTranslation.js`.
3. Keep the key sets identical and test the screens using the new language.
4. Ask a fluent native speaker to review translations marked `TODO-native-review`; do not publish those placeholder values as final copy.

The selected language is stored as `fg_lang` in local storage.

## Frontend API integration

The frontend calls `POST /api/reports`, `GET /api/reports`, `GET /api/map/reports`, and `GET /api/alerts`. API errors are shown to the user rather than replaced with synthetic success data. Photo submissions are saved by the backend during analysis; queued offline photos upload when the app reconnects. A missing model returns an unknown diagnosis with no confidence score.

When enabled, the backend imports the root predictor through `FLORAGUARD_PREDICTOR=predictor:predict_image`. Keep this unset until dependencies are installed and a reviewed, activated model is available. The AI classifier's confidence is separate from its prototype visual-severity estimate and the backend's community risk score.

## PWA notes

The root `manifest.json` and `sw.js` provide installability and a basic offline app shell. Offline photo submissions are queued in browser local storage and uploaded when connectivity returns. A production release should add durable queue management, consent, and secure storage appropriate to the data.

## Important configuration

Update `AREA_NAME` and `MAP_CENTER` in `src/config.js` for the deployment. Map data intentionally uses coarse zone-level areas and does not display farm names or precise farm locations.
