from __future__ import annotations
from celery import shared_task
from django.db import transaction
from django.conf import settings
from pathlib import Path
import joblib
import json

from django.utils import timezone
from datetime import timedelta
from analyticsapp.models import Event

from sklearn.linear_model import LogisticRegression
from sklearn.utils.class_weight import compute_class_weight
import numpy as np

from platformapp.models import Tenant
from analyticsapp.models import RiskSignal
from payments.models import Payment
from .ml.fraud_vectorizer import FraudVectorizer
from .features.fraud import extract_mobile_money_features
import json

def _model_dir(tenant_id: str) -> Path:
    d = Path(settings.MEDIA_ROOT) / "models" / str(tenant_id)
    d.mkdir(parents=True, exist_ok=True)
    return d

def _backoff(attempt: int) -> int:
    return min(60, 2 ** attempt)  # 1,2,4,8,16,32,60,...

@shared_task(bind=True, max_retries=6)
def run_job_task(self, job_id: int):
    job = AiJob.objects.select_related("tenant","model").get(id=job_id)
    m = job.model
    p = get_provider(m)

    try:
        job.mark_running()
        payload = job.input_json or {}

        if job.job_type == AiJob.JobType.TRAIN:
            out = p.train(payload)
            m.status = "ready"
            m.metrics_json = out.get("metrics", m.metrics_json)
            m.save(update_fields=["status", "metrics_json"])
            job.mark_done(out)
            return

        if job.job_type == AiJob.JobType.INFER:
            result = p.infer_one(payload)
            with transaction.atomic():
                AiPrediction.objects.create(
                    tenant=job.tenant, model=m,
                    entity_type=payload.get("entity_type","generic"),
                    entity_id=payload.get("entity_id"),
                    label=result.get("label"), score=result.get("score"),
                    threshold=result.get("threshold"), explain_json=result.get("explain"),
                    features_hash=payload.get("features_hash"),
                )
            job.mark_done(result)
            return

        if job.job_type == AiJob.JobType.BATCH_INFER:
            rows: List[Dict[str, Any]] = payload.get("items") or []
            kps = []
            per_sec = max(1, job.throttle_per_sec)
            for idx, item in enumerate(rows, start=1):
                result = p.infer_one(item)
                AiPrediction.objects.create(
                    tenant=job.tenant, model=m,
                    entity_type=item.get("entity_type","generic"),
                    entity_id=item.get("entity_id"),
                    label=result.get("label"), score=result.get("score"),
                    threshold=result.get("threshold"), explain_json=result.get("explain"),
                    features_hash=item.get("features_hash"),
                )
                if idx % per_sec == 0:
                    sleep(1)  # throttle
                if idx % 20 == 0:
                    job.progress = round(100.0 * idx / max(1, len(rows)), 2)
                    job.save(update_fields=["progress"])
            job.mark_done({"count": len(rows)})
            return

        if job.job_type == AiJob.JobType.RECOMMEND:
            result = p.infer_one(payload)  # provider returns {items:[...]}
            AiRecommendation.objects.create(
                tenant=job.tenant, model=m,
                customer_id=payload.get("customer_id"),
                context=payload.get("context", "generic"),
                algo=payload.get("algo","personalized"),
                items_json=result.get("items", []),
                expires_at=payload.get("expires_at"),
            )
            job.mark_done(result)
            return

        job.mark_failed("Unknown job_type")

    except Exception as e:
        job.attempts += 1
        job.save(update_fields=["attempts"])
        try:
            raise self.retry(countdown=_backoff(job.attempts), exc=e)
        except self.MaxRetriesExceededError:
            job.mark_failed(str(e))
            raise

@shared_task(bind=True, max_retries=6)
def send_campaign_task(self, job_id: int):
    """
    Optional: if you drive AI-powered campaigns here (e.g., smart audiences). Kept for parity with marketing app.
    """
    # No-op placeholder; your marketing app already has the real one.
    return {"ok": True}

@shared_task
def train_fraud_model(tenant_id: str, min_samples: int = 200):
    """
    Train a simple logistic regression model on tenant RiskSignal + Payment labels.
    Label mapping:
      - Payment.status in {"chargeback","refunded","failed"} => y=1 (fraud/unsafe)
      - Payment.status in {"succeeded","paid","authorized"}  => y=0 (legit)
    Falls back if not enough labeled data.
    """
    tenant = Tenant.objects.get(id=tenant_id)
    # Join RiskSignal → Payment via entity_id
    signals = (RiskSignal.objects
               .filter(tenant=tenant, entity_type="payment")
               .values("entity_id","features"))

    X_dicts, y = [], []
    for row in signals.iterator(chunk_size=1000):
        pid = row["entity_id"]
        feats = row["features"] or {}
        try:
            p = Payment.objects.get(id=pid, tenant=tenant)
        except Payment.DoesNotExist:
            continue
        status = (p.status or "").lower()
        if status in ("chargeback","refunded","failed"):
            label = 1
        elif status in ("succeeded","paid","authorized"):
            label = 0
        else:
            continue
        X_dicts.append(feats)
        y.append(label)

    if len(y) < min_samples:
        return {"ok": False, "reason": f"not_enough_samples:{len(y)}"}

    vec = FraudVectorizer().fit(X_dicts)
    X = vec.transform(X_dicts)
    y = np.array(y)

    # handle imbalance
    classes = np.array([0,1])
    weights = compute_class_weight(class_weight="balanced", classes=classes, y=y)
    class_weight = {int(c): float(w) for c, w in zip(classes, weights)}

    clf = LogisticRegression(max_iter=1000, class_weight=class_weight)
    clf.fit(X, y)

    # persist artifacts
    outdir = _model_dir(str(tenant.id))
    joblib.dump(vec, outdir / "fraud_vectorizer.joblib")
    joblib.dump(clf, outdir / "fraud_lr.joblib")
    return {"ok": True, "n": int(len(y))}


@shared_task
def autolabel_payments(tenant_id: str, days: int = 7):
    """
    Nightly: convert Payment.status → labels into analytics 'risk_label' Events.
      y=1 for {chargeback, refunded, failed, blocked}
      y=0 for {succeeded, paid, authorized, captured}
    """
    tenant = Tenant.objects.get(id=tenant_id)
    since = timezone.now() - timedelta(days=days)

    good = {"succeeded", "paid", "authorized", "captured"}
    bad  = {"chargeback", "refunded", "failed", "blocked"}

    qs = Payment.objects.filter(tenant=tenant, updated_at__gte=since).values("id", "status", "updated_at")
    created = 0
    updated = 0

    with transaction.atomic():
        for row in qs.iterator(chunk_size=1000):
            st = (row["status"] or "").lower()
            if st in good:
                y = 0
            elif st in bad:
                y = 1
            else:
                continue

            # upsert Event(name="risk_label", props={"y": y})
            ev, was_created = Event.objects.get_or_create(
                tenant=tenant,
                name="risk_label",
                profile=None,
                defaults={"props": {"y": y, "payment_id": str(row["id"])}}
            )
            if not was_created:
                props = ev.props or {}
                if props.get("y") != y:
                    props["y"] = y
                    props["payment_id"] = str(row["id"])
                    ev.props = props
                    ev.save(update_fields=["props"])
                    updated += 1
            else:
                created += 1

    return {"ok": True, "created": created, "updated": updated}


@shared_task
def compute_fraud_metrics(tenant_id: str, days: int = 30):
    from sklearn.metrics import roc_auc_score, average_precision_score
    tenant = Tenant.objects.get(id=tenant_id)
    since = timezone.now() - timedelta(days=days)

    good = {"succeeded", "paid", "authorized", "captured"}
    bad  = {"chargeback", "refunded", "failed", "blocked"}

    payments = Payment.objects.filter(tenant=tenant, created_at__gte=since).values("id","status")
    ids, y = [], []
    for p in payments:
        st = (p["status"] or "").lower()
        if st in good: y.append(0); ids.append(p["id"])
        elif st in bad: y.append(1); ids.append(p["id"])

    if not y:
        return {"ok": False, "reason": "no_labels"}

    # try ML, fallback to rules
    artifacts = _load_fraud_artifacts(tenant.id)
    feats = {str(s["entity_id"]): (s.get("features") or {}) for s in
             RiskSignal.objects.filter(tenant=tenant, entity_type="payment", entity_id__in=ids)
             .values("entity_id","features")}

    if artifacts:
        vec, mdl = artifacts
        X = [feats.get(str(pid), {}) for pid in ids]
        if any(X):
            probs = mdl.predict_proba(vec.transform(X))[:,1].tolist()
        else:
            artifacts = None

    if not artifacts:
        score_map = {str(s["entity_id"]): float(s["score"] or 0.5) for s in
                     RiskSignal.objects.filter(tenant=tenant, entity_type="payment", entity_id__in=ids)
                     .values("entity_id","score")}
        probs = [score_map.get(str(pid), 0.5) for pid in ids]

    try: roc = float(roc_auc_score(y, probs))
    except Exception: roc = None
    try: pr  = float(average_precision_score(y, probs))
    except Exception: pr = None

    out = {"ok": True, "window_days": days, "n": len(y), "roc_auc": roc, "pr_auc": pr}
    d = _model_dir(str(tenant.id))
    (d / "fraud_metrics.json").write_text(json.dumps(out, indent=2))
    return out
