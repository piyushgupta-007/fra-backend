"""
Thin wrapper around the Groq API for generating plain-language anomaly
summaries for a given district. Groq's API is OpenAI-compatible and runs
open models (Llama, etc.) at very high speed — free tier is generous,
good fit for a hackathon demo.

Requires:
    pip install groq
    export GROQ_API_KEY=gsk_...          (PowerShell: $env:GROQ_API_KEY="gsk_...")

If Atharv hands you prompt-engineering code at Hour 7, drop the improved
prompt into `build_prompt()` below and everything else keeps working.
"""

import os
from typing import Optional

try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None

# Fast, capable, and free-tier friendly. Swap for another Groq-hosted
# model name if the team prefers (e.g. "llama-3.1-8b-instant" for speed).
MODEL = "llama-3.3-70b-versatile"


def _get_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY environment variable not set. "
            "PowerShell: $env:GROQ_API_KEY=\"your_key_here\"  |  "
            "macOS/Linux: export GROQ_API_KEY=your_key_here"
        )
    if Groq is None:
        raise RuntimeError(
            "The 'groq' package is not installed. Run: pip install groq"
        )
    return Groq(api_key=api_key)


def build_prompt(district: dict) -> str:
    """Build the prompt sent to the model for a single district's summary."""
    return f"""You are helping a government forest-rights official quickly understand
a potential data anomaly in Forest Rights Act (FRA) claim processing.

District: {district.get('district_name')}, {district.get('state')}
Claims filed: {district.get('claims_filed')}
Claims approved: {district.get('claims_approved')}
Average pending days: {district.get('pending_days_avg')}
Land area (hectares): {district.get('land_area_ha')}
Flagged anomaly reason(s): {district.get('anomaly_reason') or 'None flagged'}

Write a short (3-4 sentence) plain-language explanation of what this data
suggests is happening in this district, why it might have been flagged
(if it was), and one concrete recommended next step for the state nodal
officer. Avoid jargon. Do not repeat the raw numbers verbatim; interpret them."""


def generate_ai_summary(district: dict) -> str:
    """
    Call the Groq API to get a plain-language summary for one district.
    Falls back to a rule-based summary if the API call fails, so the demo
    never breaks on stage even without a live key.
    """
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": build_prompt(district)}],
        )
        text = response.choices[0].message.content
        return (text or "").strip() or _fallback_summary(district)
    except Exception as exc:  # noqa: BLE001 - demo resilience over precision
        return _fallback_summary(district, error=str(exc))


def _fallback_summary(district: dict, error: Optional[str] = None) -> str:
    """Offline/no-API-key fallback so endpoints still return something useful."""
    name = district.get("district_name", "This district")
    state = district.get("state", "")
    reason = district.get("anomaly_reason")
    if reason:
        base = (
            f"{name}, {state} has been flagged because {reason.lower()}. "
            "This pattern typically points to processing backlogs or verification "
            "delays at the sub-divisional level. Recommended next step: the state "
            "nodal officer should audit pending claims in this district and confirm "
            "field-level verification staffing."
        )
    else:
        base = (
            f"{name}, {state} shows no anomalies under current rules. "
            "Claims are being processed within expected timeframes and approval "
            "rates. No immediate action needed."
        )
    if error:
        base += f"\n\n[Note: AI summary service unavailable, showing rule-based summary. Detail: {error}]"
    return base
