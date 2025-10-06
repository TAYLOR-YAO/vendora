from __future__ import annotations
from typing import Dict, Any, List, Tuple
from sklearn.feature_extraction import DictVectorizer

NUMERIC = {
    "amount", "customer_age_days", "cust_lifetime_orders", "cust_lifetime_amount",
    "txn_hr", "hrs_since_account_creation", "txn_1h", "txn_24h", "txn_7d",
    "chargeback_90d", "declines_24h"
}
CATEGORICAL = {"amt_bucket", "geo_country"}

KEEP_BINARIES = {"is_night", "is_new_customer"}

def prepare(dict_features: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only supported keys and coerce types."""
    out = {}
    for k in NUMERIC:
        v = dict_features.get(k)
        try:
            out[k] = float(v) if v is not None else 0.0
        except Exception:
            out[k] = 0.0
    for k in CATEGORICAL:
        v = dict_features.get(k)
        if v is None:
            continue
        out[f"{k}={v}"] = 1  # one-hot via DictVectorizer
    for k in KEEP_BINARIES:
        out[k] = 1.0 if dict_features.get(k) else 0.0
    return out

class FraudVectorizer:
    def __init__(self):
        self.dv = DictVectorizer(sparse=False)

    def fit(self, examples: List[Dict[str, Any]]):
        X = [prepare(d) for d in examples]
        self.dv.fit(X)
        return self

    def transform(self, examples: List[Dict[str, Any]]):
        X = [prepare(d) for d in examples]
        return self.dv.transform(X)

    def feature_names(self) -> List[str]:
        return list(self.dv.get_feature_names_out())
