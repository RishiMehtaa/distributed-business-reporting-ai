# SignalFlow AI — Basic End-User UI

## Features
- Calls your existing `POST http://localhost:8000/run-demo` API.
- Supports `normal`, `anomaly`, and `bad_data`.
- Shows KPI cards, monthly trend, regional comparison, workflow stage outcomes, agent outputs, critic verdict, numeric QA, and report/chart artifact paths.
- Responsive layout for desktop and mobile.

## Run
1. Keep Docker Compose backend running.
2. Open `index.html` in a browser.
3. Choose a scenario and click **Run workflow**.

## If the browser blocks the request (CORS)
Add this near the top of `orchestrator/main.py`, after the FastAPI app is created:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local demo only; restrict for public deployment
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Then rebuild:
```bash
docker compose up -d --build orchestrator
```

For a public deployment, replace `allow_origins=["*"]` with your exact frontend domain. Never put your Gemini API key in frontend code.

## Artifact note
The backend returns paths inside the reporting container (for example `/app/output/...`). This UI displays those paths but does not present them as downloadable links. Browser downloads require an artifact-serving endpoint or shared storage.
