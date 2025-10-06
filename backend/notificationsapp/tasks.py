from celery import shared_task
from django.utils import timezone
from .models import NotificationDispatch, NotificationTemplate
from .utils import render_preview, log_delivery

# You can swap these shims for real implementations (SendGrid, Twilio, Expo, Webhooks, etc.)
def _send_email(to_address: str, subject: str, body: str, attachments=None) -> str:
    # return provider reference/id
    return "email:mock-ref-123"

def _send_sms(to_address: str, body: str) -> str:
    return "sms:mock-ref-123"

def _send_push(to_user_id: str, subject: str, body: str) -> str:
    return "push:mock-ref-123"

def _send_webhook(url: str, payload: dict) -> str:
    return "webhook:mock-ref-123"


@shared_task
def deliver_dispatch_async(dispatch_id: int):
    d = NotificationDispatch.objects.select_related("template", "tenant").filter(id=dispatch_id).first()
    if not d or d.status in ("sent", "cancelled"):
        return

    if d.schedule_at and d.schedule_at > timezone.now():
        # Requeue later (depends on your Celery beat strategy)
        deliver_dispatch_async.apply_async((dispatch_id,), eta=d.schedule_at)
        return

    d.status = "sending"
    d.save(update_fields=["status"])

    try:
        # Determine template (if missing, allow raw payload send for system/webhook)
        subject, body = "", ""
        if d.template:
            rendered = render_preview(d.template, d.payload_json or {})
            if "error" in rendered:
                raise ValueError(rendered["error"])
            subject, body = rendered.get("subject", ""), rendered.get("body", "")

        # Respect preferences/quiet hours/digests here if needed (resolve by user_id or address)
        # ...

        ref = None
        if d.channel == "email":
            ref = _send_email(d.to_address or "", subject=subject, body=body, attachments=d.attachments)
            provider = "email"
        elif d.channel == "sms":
            ref = _send_sms(d.to_address or "", body=body or subject)
            provider = "sms"
        elif d.channel == "push":
            ref = _send_push(str(d.to_user_id or ""), subject=subject, body=body)
            provider = "push"
        elif d.channel == "webhook":
            ref = _send_webhook(d.to_address or "", d.payload_json or {})
            provider = "webhook"
        else:
            raise ValueError(f"Unsupported channel: {d.channel}")

        d.provider_ref = ref
        d.sent_at = timezone.now()
        d.status = "sent"
        d.save(update_fields=["provider_ref", "sent_at", "status"])

        log_delivery(dispatch=d, provider=provider, status="sent", provider_ref=ref, meta={"len": len((body or ""))})
    except Exception as e:
        d.status = "failed"
        d.error_message = str(e)
        d.save(update_fields=["status", "error_message"])
        log_delivery(dispatch=d, provider="internal", status="failed", meta={"error": str(e)})
