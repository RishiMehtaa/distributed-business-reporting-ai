
from fastapi import FastAPI, HTTPException  # pyright: ignore[reportMissingImports]
from pydantic import BaseModel, Field 
from typing import Dict, Any
import os
import json
import time

app = FastAPI(title="Hybrid AI Insights Service")


class Task(BaseModel):
    kpis: Dict[str, Any]
    profile: Dict[str, Any] = Field(default_factory=dict)
    question: str = "Summarize business performance."
    extra_context: str = ""


def get_api_key():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY is missing. Add it to .env and restart Docker Compose."
        )
    return key

def ask_gemini(role, goal, prompt, context):
    """Use Gemini directly for straightforward analytical tasks."""
    key = get_api_key()

    try:
        from google import genai
        from google.genai import types
        

        start_total = time.perf_counter()

        client = genai.Client(api_key=key)
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        print(f"[TIMING] Gemini client setup: " f"{time.perf_counter() - start_total:.2f}s", flush=True)

        full_prompt = f"""
Role: {role}
Objective: {goal}

Instructions:
{prompt}

Evidence (use only the supplied facts):
{json.dumps(context, ensure_ascii=False, default=str)}

Rules:
- Never invent metrics or facts.
- Distinguish observations from hypotheses.
- Do not claim causation from aggregate data alone.
- State important limitations and missing information.
- Give concise, actionable business recommendations.
"""

        start_api = time.perf_counter()
        print(f"[TIMING] Gemini request started; model={model}", flush=True)

        response = client.models.generate_content(
                    model=model,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(
                            thinking_level="low"
                        )
                    )
                )

        print(f"[TIMING] Gemini API response received: "
                f"{time.perf_counter() - start_api:.2f}s", flush=True)

        print(f"[TIMING] Total ask_gemini time: "
                f"{time.perf_counter() - start_total:.2f}s", flush=True)

        result = getattr(response, "text", None)
        if not result or not result.strip():
            raise HTTPException(
                status_code=502,
                detail="Gemini returned an empty response."
            )

        return result.strip()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API error: {type(e).__name__}: {e}"
        )


def ask_crew(role, goal, prompt, context):
    """Retain CrewAI for the independent report critic."""
    key = get_api_key()

    try:
        from crewai import Agent, Task as CrewTask, Crew, Process, LLM

        llm = LLM(
            model=f"gemini/{os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')}",
            api_key=key,
            temperature=0.2
        )

        agent = Agent(
            role=role,
            goal=goal,
            backstory=(
                "Careful independent business reviewer. Never invent metrics "
                "or claim causation from aggregate data."
            ),
            llm=llm,
            verbose=False,
            allow_delegation=False
        )

        task = CrewTask(
            description=(
                prompt
                + "\nEvidence (use only supplied facts):\n"
                + json.dumps(context, ensure_ascii=False, default=str)
            ),
            expected_output=(
                "Concise, evidence-grounded review with a clear verdict."
            ),
            agent=agent
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False
        )

        return str(crew.kickoff())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"CrewAI critic error: {type(e).__name__}: {e}"
        )


@app.get("/health")
def health():
    return {
        "service": "insights",
        "status": "ok",
        "llm_configured": bool(
            os.getenv("GEMINI_API_KEY", "").strip()
        ),
        "architecture": "direct Gemini + CrewAI critic"
    }


@app.post("/business-analysis")
def analysis(t: Task):
    result = ask_gemini(
        "Business Analyst",
        "Interpret KPIs and suggest next steps",
        (
            "Give 3-5 observations, 2 prioritized actions, and caveats. "
            "Separate measured facts from hypotheses. "
            "Answer this business question: " + t.question
        ),
        {
            "kpis": t.kpis,
            "profile": t.profile,
            "context": t.extra_context
        }
    )

    return {"agent": "business_analyst", "result": result}


@app.post("/chart-advice")
def chart(t: Task):
    result = ask_gemini(
        "Visualization Advisor",
        "Recommend clear and accurate charts",
        (
            "Recommend appropriate charts for monthly, regional, and "
            "category sales where the available fields support them. "
            "For each recommendation, explain its purpose and limitations. "
            "Do not assume a field exists unless it is supplied."
        ),
        {"kpis": t.kpis}
    )

    return {"agent": "chart_advisor", "result": result}


@app.post("/investigate")
def investigate(t: Task):
    result = ask_gemini(
        "Anomaly Investigator",
        "Investigate unusual business performance patterns",
        (
            "Investigate the reported material decline using supplied "
            "aggregates. Identify observed patterns, plausible hypotheses, "
            "and specific next checks. Do not present hypotheses as facts."
        ),
        {
            "kpis": t.kpis,
            "context": t.extra_context
        }
    )

    return {"agent": "Anomaly Investigator", "result": result}


@app.post("/critique")
def critique(t: Task):
    result = ask_crew(
        "Independent Report Critic",
        "Detect unsupported claims and analytical overreach",
        (
            "Review the candidate analysis for unsupported numeric claims, "
            "causal overreach, missing caveats, and conclusions not justified "
            "by the supplied evidence. Begin with exactly "
            "'VERDICT: PASS' or 'VERDICT: REVIEW REQUIRED', then list issues. "
            "Use REVIEW REQUIRED if a material issue is found."
        ),
        {
            "kpis": t.kpis,
            "candidate": t.extra_context
        }
    )

    upper_result = result.upper()
    passed = (
        "VERDICT: PASS" in upper_result
        and "REVIEW REQUIRED" not in upper_result
    )

    return {
        "agent": "independent_critic",
        "result": result,
        "passed": passed
    }
