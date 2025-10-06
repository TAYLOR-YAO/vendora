from __future__ import annotations
from typing import Dict, Any, List
import time
import random
import requests
from .models import AiModel

class ProviderBase:
    def __init__(self, model: AiModel):
        self.m = model

    def infer_one(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def infer_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.infer_one(p) for p in items]

    def train(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Return training metrics
        return {"status": "ok"}

# --- Dummy provider: fast, great for dev & fallback in poor connectivity ---
class DummyProvider(ProviderBase):
    def infer_one(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        task = self.m.task
        if task == AiModel.AiTask.FRAUD:
            score = round(random.random(), 6)
            return {"label": "fraud" if score > 0.85 else "ok", "score": score, "explain": {"rule":"random"}}
        if task == AiModel.AiTask.RECOMMENDATION:
            items = payload.get("candidates") or ["p1","p2","p3","p4","p5"]
            random.shuffle(items)
            return {"items": items[: payload.get("k", 5)]}
        # default
        return {"score": round(random.random(), 6)}

# --- HTTP provider: call external inference/training endpoints ---
class HttpProvider(ProviderBase):
    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.m.auth_token:
            h["Authorization"] = f"Bearer {self.m.auth_token}"
        return h

    def infer_one(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = (self.m.endpoint_url or "").rstrip("/") + "/infer"
        r = requests.post(url, json={"model": self.m.name, "version": self.m.version, "payload": payload}, headers=self._headers(), timeout=20)
        r.raise_for_status()
        return r.json()

    def train(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = (self.m.endpoint_url or "").rstrip("/") + "/train"
        r = requests.post(url, json={"model": self.m.name, "version": self.m.version, "params": params}, headers=self._headers(), timeout=60)
        r.raise_for_status()
        return r.json()

def get_provider(model: AiModel) -> ProviderBase:
    if model.provider == AiModel.ProviderKind.HTTP:
        return HttpProvider(model)
    return DummyProvider(model)
