from typing import Optional, Dict, Any, List
from django.utils.dateparse import parse_datetime
from django.template import engines
from .models import NotificationDispatch, NotificationLog, NotificationTemplate, Topic

def _django_render_string(template_string: str, context: Dict[str, Any]) -> str:
    # Simple, fast inline rendering; you can switch to Jinja2 if preferred.
    django_engine = engines["django"]
    tpl = django_engine.from_string(template_string)
    return tpl.render(context)

def render_preview(template: NotificationTemplate, payload: Dict[str, Any]) -> Dict[str, str]:
    subject = template.subject or ""
    body = template.body or ""
    try:
        subject_r = _django_render_string(subject, payload) if subject else ""
        body_r = _django_render_string(body, payload)
        return {"subject": subject_r, "body": body_r}
    except Exception as e:
        return {"error": str(e)}

def queue_notification(
    tenant,
    template_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    to_user_id: Optional[str] = None,
    to_address: Optional[str] = None,
    channel: str = "email",
    payload: Optional[Dict[str, Any]] = None,
    schedule_at: Optional[str] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
) -> NotificationDispatch:
    schedule_dt = parse_datetime(schedule_at) if isinstance(schedule_at, str) else schedule_at
    tmpl = NotificationTemplate.objects.filter(id=template_id, tenant=tenant).first() if template_id else None
    topic = Topic.objects.filter(id=topic_id, tenant=tenant).first() if topic_id else None

    return NotificationDispatch.objects.create(
        tenant=tenant,
        template=tmpl,
        topic=topic,
        to_user_id=to_user_id,
        to_address=to_address,
        channel=channel,
        payload_json=payload or {},
        schedule_at=schedule_dt,
        attachments=attachments or [],
        status="queued",
    )

def log_delivery(dispatch: NotificationDispatch, provider: str, status: str = "sent", provider_ref: Optional[str] = None, meta: Optional[Dict[str, Any]] = None):
    return NotificationLog.objects.create(
        tenant=dispatch.tenant,
        dispatch=dispatch,
        provider=provider,
        status=status,
        provider_ref=provider_ref,
        meta_json=meta or {},
    )
