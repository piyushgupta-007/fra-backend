# PS-7 FRA Monitoring — Backend

Backend API for the AI-powered Decision Support System for Forest Rights Act
(FRA) Monitoring. Built with **FastAPI** so Roneet & Piyush get free
interactive docs at `/docs`, and Atharv's prompt code can drop straight into
`claude_client.py`.

## 1. Setup (Hour 0-1)

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Optional but recommended — enables real AI summaries.
# Without this, /api/ai-summary/<district> still works using a
# rule-based fallback so the demo never breaks.
export ANTHROPIC_API_KEY=your_key_here
```

## 2. Run the server

```bash
uvicorn app:app --reload --port 8000
```

- API base URL: `http://127.0.0.1:8000`
- Interactive Swagger docs: `http://127.0.0.1:8000/docs`

## 3. Project structure

```
fra-backend/
├── app.py              # FastAPI app + all endpoints
├── anomaly.py           # Anomaly detection rules (pending days, approval rate, land mismatch)
├── claude_client.py      # Claude API wrapper + fallback summary logic
├── data/
│   └── districts.json    # Mock FRA data, 18 districts across 8 states
├── requirements.txt
└── README.md
```

## 4. Mock data (share with team at Hour 2)

`data/districts.json` contains 18 districts across Madhya Pradesh,
Maharashtra, Odisha, Chhattisgarh, Telangana, Kerala, Assam, and Jharkhand.
Each record has:

```json
{
  "district_name": "Dindori",
  "state": "Madhya Pradesh",
  "claims_filed": 9800,
  "claims_approved": 1600,
  "pending_days_avg": 210,
  "land_area_ha": 28900,
  "anomaly": true,
  "anomaly_reason": "Approval rate below 20% and average pending days exceed 180"
}
```

> Note: the API recomputes `anomaly` / `anomaly_reason` live from the rules
> in `anomaly.py` rather than trusting the static JSON values, so the numbers
> stay consistent even if someone edits the JSON by hand.

## 5. API Endpoints (live by Hour 5)

### `GET /api/districts`
Returns all district data with claim stats.

```json
{ "count": 18, "districts": [ { ... }, { ... } ] }
```

### `GET /api/anomalies`
Returns only flagged/anomaly districts.

```json
{ "count": 7, "anomalies": [ { ... } ] }
```

### `GET /api/summary`
State-wise aggregated stats (sorted worst-first by anomaly count) — feeds the
decision-support panel.

```json
{
  "state_count": 8,
  "summary": [
    {
      "state": "Chhattisgarh",
      "district_count": 3,
      "total_claims_filed": 42900,
      "total_claims_approved": 25700,
      "total_land_area_ha": 112700,
      "anomaly_count": 1,
      "avg_pending_days": 131.7,
      "approval_rate_pct": 59.9
    }
  ]
}
```

### `GET /api/ai-summary/<district>`
Plain-language, Claude-generated anomaly explanation for one district
(case-insensitive match on `district_name`).

```
GET /api/ai-summary/Dindori
```

```json
{
  "district": "Dindori",
  "state": "Madhya Pradesh",
  "anomaly": true,
  "anomaly_reason": "Approval rate below 20% and average pending days exceed 180",
  "ai_summary": "Dindori shows a large backlog of unapproved claims relative to..."
}
```

## 6. Anomaly rules (`anomaly.py`)

| Rule | Condition |
|---|---|
| Slow processing | `pending_days_avg > 180` |
| Low approval | `claims_approved / claims_filed < 20%` |
| Land mismatch (placeholder) | hectares-per-claim outside a plausible 0.5–6 ha range |

Swap the land-mismatch placeholder for a real Bhuvan shapefile cross-check
if time allows after Hour 6.

## 7. Integration checklist

- [x] Hour 2 — `data/districts.json` ready to share with Roneet & Piyush
- [x] Hour 5 — all four endpoints live and CORS-enabled for frontend calls
- [ ] Hour 7 — drop Atharv's improved prompt into `claude_client.build_prompt()`
- [ ] Confirm `ANTHROPIC_API_KEY` is set before the live demo (fallback works
      without it, but real AI summaries are more impressive)
