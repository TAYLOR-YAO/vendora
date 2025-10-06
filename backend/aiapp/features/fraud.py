from __future__ import annotations
from typing import Dict, Any
from datetime import datetime, timedelta, timezone

def _hrs_ago(ts: datetime) -> float:
    now = datetime.now(timezone.utc)
    return max(0.0, (now - ts).total_seconds() / 3600.0)

def extract_mobile_money_features(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standardized schema (works across TMoney, MTN, Orange Money, etc.)
    Expected input (examples):
      amount, currency, msisdn, payer_name,
      ip, device_fp, geo_country, geo_lat, geo_lng,
      created_at (ISO str),
      customer: {id, age_days, lifetime_orders, lifetime_amount},
      merchant: {id, risk_level},from payments.models import Payment
      history: {last_1h_txn, last_24h_txn, last_7d_txn, chargeback_90d, declines_24h}
    """
    amt = float(payload.get("amount", 0))
    customer = payload.get("customer") or {}
    history = payload.get("history") or {}
    created_at = payload.get("created_at")
    try:
        created_dt = datetime.fromisoformat(created_at.replace("Z","+00:00")) if created_at else datetime.now(timezone.utc)
    except Exception:
        created_dt = datetime.now(timezone.utc)

    feats = {
        "amount": amt,
        "amt_bucket": "high" if amt >= 500000 else "med" if amt >= 100000 else "low",
        "customer_age_days": int(customer.get("age_days", 0)),
        "cust_lifetime_orders": int(customer.get("lifetime_orders", 0)),
        "cust_lifetime_amount": float(customer.get("lifetime_amount", 0)),
        "txn_hr": created_dt.hour,
        "hrs_since_account_creation": float(customer.get("age_days", 0)) * 24.0,
        "txn_1h": int(history.get("last_1h_txn", 0)),
        "txn_24h": int(history.get("last_24h_txn", 0)),
        "txn_7d": int(history.get("last_7d_txn", 0)),
        "chargeback_90d": int(history.get("chargeback_90d", 0)),
        "declines_24h": int(history.get("declines_24h", 0)),
        "ip": payload.get("ip"),
        "device_fp": payload.get("device_fp"),
        "geo_country": payload.get("geo_country", "NA"),
    }
    # simple embeddings-ready features:
    feats["is_night"] = 1 if feats["txn_hr"] < 6 else 0
    feats["is_new_customer"] = 1 if feats["customer_age_days"] <= 7 else 0
    return feats


class RiskRuleEngine:
    """
    Simple rule template combining additive weights + bucketing.
    Tweak thresholds with real data; works well as guardrails even when you later plug ML.
    """
    def __init__(self, weights=None, block_threshold=0.92, high_threshold=0.75, med_threshold=0.5):
        self.w = {
            "high_amt": 0.35,
            "night_new": 0.2,
            "burst_txn": 0.2,
            "recent_declines": 0.15,
            "chargebacks": 0.25,
            "hot_device": 0.25,  # many customers on same device
        }
        if weights:
            self.w.update(weights)
        self.block_th = block_threshold
        self.high_th = high_threshold
        self.med_th = med_threshold

    def score(self, feats: Dict[str, Any], device_usage_count: int = 1) -> (float, list):
        s = 0.0
        hit = []

        if feats.get("amt_bucket") == "high":
            s += self.w["high_amt"]; hit.append("high_amt")
        if feats.get("is_night") and feats.get("is_new_customer"):
            s += self.w["night_new"]; hit.append("night_new")
        if feats.get("txn_1h", 0) >= 3 or feats.get("txn_24h", 0) >= 10:
            s += self.w["burst_txn"]; hit.append("burst_txn")
        if feats.get("declines_24h", 0) >= 2:
            s += self.w["recent_declines"]; hit.append("recent_declines")
        if feats.get("chargeback_90d", 0) >= 1:
            s += self.w["chargebacks"]; hit.append("chargebacks")
        if device_usage_count >= 5:
            s += self.w["hot_device"]; hit.append("hot_device")

        s = min(0.99, s)  # clamp
        if s >= self.block_th: bucket = "block"
        elif s >= self.high_th: bucket = "high"
        elif s >= self.med_th: bucket = "med"
        else: bucket = "low"
        return s, hit, bucket
