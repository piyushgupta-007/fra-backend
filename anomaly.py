"""
Anomaly detection logic for FRA claim data.

Rules:
1. Flag if pending_days_avg > 180
2. Flag if approval rate (claims_approved / claims_filed) < 20%
3. Flag if land area looks mismatched (placeholder rule using a simple
   sanity check: land_area_ha should be reasonably proportional to
   claims_filed. Real implementation would cross-check against Bhuvan
   shapefile records; here we flag absurd outliers as a stand-in.)
"""

from typing import Optional


def approval_rate(claims_filed: int, claims_approved: int) -> float:
    """Return approval rate as a fraction (0.0 - 1.0). Avoids divide-by-zero."""
    if not claims_filed:
        return 0.0
    return claims_approved / claims_filed


def land_area_mismatch(district: dict) -> bool:
    """
    Placeholder land-record mismatch check.
    Flags if land area per claim filed is implausibly small or large,
    which in a real system would be replaced by a cross-check against
    Bhuvan / district shapefile records.
    """
    claims_filed = district.get("claims_filed", 0)
    land_area_ha = district.get("land_area_ha", 0)
    if not claims_filed:
        return False
    ha_per_claim = land_area_ha / claims_filed
    # Reasonable FRA claims are typically 1-4 ha/household on average.
    # Outside 0.5 - 6 ha/claim is treated as a data mismatch signal.
    return ha_per_claim < 0.5 or ha_per_claim > 6

def detect_anomaly(district: dict) -> tuple[bool, Optional[str]]:
    """
    Run all anomaly rules against a single district record.
    Returns (is_anomaly, reason_string_or_None).
    """
    reasons = []

    if district.get("pending_days_avg", 0) > 180:
        reasons.append("average pending days exceed 180")

    rate = approval_rate(district.get("claims_filed", 0), district.get("claims_approved", 0))
    if rate < 0.20:
        reasons.append(f"approval rate below 20% ({round(rate * 100)}%)")

    if land_area_mismatch(district):
        reasons.append("land area records appear mismatched against claims filed")

    if reasons:
        # Capitalize first reason for a clean sentence, join with " and "
        reason_text = " and ".join(reasons)
        return True, reason_text[0].upper() + reason_text[1:]

    return False, None


def annotate_districts(districts: list[dict]) -> list[dict]:
    """
    Recompute anomaly flags for a list of districts using live rules
    (rather than trusting whatever static value is in the JSON file).
    Returns a new list of district dicts with anomaly/anomaly_reason set.
    """
    annotated = []
    for d in districts:
        is_anomaly, reason = detect_anomaly(d)
        new_d = dict(d)
        new_d["anomaly"] = is_anomaly
        new_d["anomaly_reason"] = reason
        annotated.append(new_d)
    return annotated
