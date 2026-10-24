# Distributed Multi-Agent AI Business Reporting

CrewAI + FastAPI prototype demonstrating distributed services, parallel analysis, conditional anomaly investigation, independent AI critique, and report generation.

## Services
- **orchestrator**: coordinates workflow and conditional routing (port 8000)
- **analytics**: deterministic data profiling and KPI calculations (8001)
- **insights**: CrewAI-powered business analyst, chart advisor, anomaly investigator and critic (8002)
- **reporting**: creates PNG charts and a Markdown executive report (8003)

These run in separate Docker containers. You can deploy each service on a separate host later by changing service URLs.

## Quick start (Windows)
1. Install Docker Desktop and start it.
2. Extract this ZIP to a folder.
3. Copy `.env.example` to `.env` and add a Gemini API key from https://aistudio.google.com/ to `GEMINI_API_KEY`.
4. In PowerShell, open the extracted folder and run `docker compose up --build`.
5. Open http://localhost:8000/docs.
6. Run `POST /run-demo` with `{"scenario":"anomaly"}`. Try `normal` and `bad_data` too.
7. Reports and chart images appear in the `output` folder.

## Behavior to demonstrate
- Profiling and KPI calculations execute concurrently.
- AI business analysis and chart advice run concurrently.
- Anomaly investigation only runs when latest month-over-month sales growth is <= -10%.
- Bad/duplicate data blocks downstream AI work.
- Independent AI critique can mark the final report REVIEW REQUIRED.
- Numeric QA independently recomputes total sales.

## Notes
This is an educational MVP, not production-ready. It uses synthetic data and does not connect to corporate Snowflake, Snowsheets, Google Sheets or Google Slides yet. Add integrations after validating the distributed workflow. Never use confidential company data without authorization. API/model quotas and free-tier terms can change.
