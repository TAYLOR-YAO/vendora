"""
Very small notification publisher using the DB.
Real systems might also push to email/SMS/webhooks/FCM, etc.
"""
from django.utils import timezone
from notificationsapp.models import Notification

def notify(tenant, kind: str, message: str, user=None, meta: dict | None = None):
    return Notification.objects.create(
        tenant=tenant,
        user=user,
        kind=kind,
        message=message[:500],
        meta=meta or {},
        sent_at=timezone.now(),
    )
