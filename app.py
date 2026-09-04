"""
PS-7: AI-powered Decision Support System for FRA Monitoring
Backend API (FastAPI)

Endpoints:
    GET /api/districts              -> all district data
    GET /api/anomalies              -> only flagged/anomaly districts
    GET /api/summary                -> state-wise aggregated stats
    GET /api/ai-summary/<district>  -> AI-generated plain-language explanation

Run locally:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here   # optional, falls back gracefully
    uvicorn app:app --reload --port 8000

Then visit http://127.0.0.1:8000/docs for interactive Swagger UI.
"""

import json
from pathlib import Path
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from anomaly import annotate_districts
from claude_client import generate_ai_summary

DATA_PATH = Path(__file__).parent / "data" / "districts.json"

app = FastAPI(
    title="FRA Monitoring API",
    description="AI-powered Decision Support System for Forest Rights Act (FRA) Monitoring",
    version="1.0.0",
)

# Allow the frontend (Roneet & Piyush's map/dashboard) to call this API
# from any origin during the hackathon. Tighten this before any real deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_districts() -> list[dict]:
    if not DATA_PATH.exists():
        raise HTTPException(status_code=500, detail=f"Data file not found at {DATA_PATH}")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    # Recompute anomaly flags live using anomaly.py rules, so the API
    # is always consistent even if the JSON file drifts.
    return annotate_districts(raw)


@app.get("/")
def root():
    return {
        "message": "FRA Monitoring API is running.",
        "endpoints": [
            "/api/districts",
            "/api/anomalies",
            "/api/summary",
            "/api/ai-summary/{district}",
        ],
    }


@app.get("/api/districts")
def get_districts():
    """Return all district data with claim stats."""
    districts = load_districts()
    return {"count": len(districts), "districts": districts}


@app.get("/api/anomalies")
def get_anomalies():
    """Return only districts currently flagged as anomalies."""
    districts = load_districts()
    flagged = [d for d in districts if d["anomaly"]]
    return {"count": len(flagged), "anomalies": flagged}


@app.get("/api/summary")
def get_summary():
    """Return state-wise aggregated stats."""
    districts = load_districts()
    state_data = defaultdict(lambda: {
        "state": "",
        "district_count": 0,
        "total_claims_filed": 0,
        "total_claims_approved": 0,
        "total_land_area_ha": 0,
        "anomaly_count": 0,
        "avg_pending_days": 0.0,
        "_pending_days_sum": 0,
    })

    for d in districts:
        s = state_data[d["state"]]
        s["state"] = d["state"]
        s["district_count"] += 1
        s["total_claims_filed"] += d["claims_filed"]
        s["total_claims_approved"] += d["claims_approved"]
        s["total_land_area_ha"] += d["land_area_ha"]
        s["anomaly_count"] += 1 if d["anomaly"] else 0
        s["_pending_days_sum"] += d["pending_days_avg"]

    summary = []
    for s in state_data.values():
        s["avg_pending_days"] = round(s["_pending_days_sum"] / s["district_count"], 1)
        s["approval_rate_pct"] = round(
            (s["total_claims_approved"] / s["total_claims_filed"]) * 100, 1
        ) if s["total_claims_filed"] else 0.0
        del s["_pending_days_sum"]
        summary.append(s)

    # Sort worst-first by anomaly count, useful for the decision-support panel
    summary.sort(key=lambda x: x["anomaly_count"], reverse=True)

    return {"state_count": len(summary), "summary": summary}


@app.get("/api/ai-summary/{district}")
def get_ai_summary(district: str):
    """
    Return an AI-generated plain-language explanation for one district.
    `district` is matched case-insensitively against district_name.
    """
    districts = load_districts()
    match = next(
        (d for d in districts if d["district_name"].lower() == district.lower()),
        None,
    )
    if match is None:
        raise HTTPException(
            status_code=404,
            detail=f"District '{district}' not found. Check /api/districts for valid names.",
        )

    summary_text = generate_ai_summary(match)
    return {
        "district": match["district_name"],
        "state": match["state"],
        "anomaly": match["anomaly"],
        "anomaly_reason": match["anomaly_reason"],
        "ai_summary": summary_text,
    }
