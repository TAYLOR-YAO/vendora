from typing import Dict, Any
from .models import Event, Workflow, WorkflowRun
from django.db import transaction

def emit_event(*, tenant, name: str, payload: Dict[str, Any]):
    return Event.objects.create(tenant=tenant, name=name, payload=payload, status="queued")

def _match(workflow: Workflow, payload: Dict[str, Any]) -> bool:
    cond = workflow.condition_json or {}
    # Simple key==value matcher; extend to DSL later
    for k, v in cond.items():
        if payload.get(k) != v:
            return False
    return True

def run_actions(workflow: Workflow, event: Event) -> str:
    """
    Execute actions_json in order. Keep it small & explicit.
    Actions supported:
      - create_invoice
      - create_shipment
      - notify (channel, template_key, to_address/to_user_id, context)
    """
    from invoicing.models import Invoice
    from shipments.models import Shipment
    from notificationsapp.utils import queue_notification
    from commerce.models import Order

    logs = []
    actions = workflow.actions_json or []
    for act in actions:
        t = act.get("action")
        if t == "create_invoice":
            oid = event.payload.get("order_id")
            order = Order.objects.get(id=oid, tenant=workflow.tenant)
            Invoice.objects.get_or_create(
                tenant=workflow.tenant, order=order,
                defaults={"number": f"INV-{order.id}", "currency": order.currency, "total_amount": order.total_amount, "status": "open"}
            )
            logs.append(f"invoice.ok:{oid}")
        elif t == "create_shipment":
            oid = event.payload.get("order_id")
            order = Order.objects.get(id=oid, tenant=workflow.tenant)
            Shipment.objects.get_or_create(tenant=workflow.tenant, order=order, defaults={"status": "pending"})
            logs.append(f"shipment.ok:{oid}")
        elif t == "notify":
            queue_notification(
                tenant=workflow.tenant,
                to_user_id=act.get("to_user_id"),
                to_address=act.get("to_address"),
                channel=act.get("channel","email"),
                template=None,
                payload=act.get("context") or {}
            )
            logs.append("notify.ok")
        else:
            logs.append(f"skip:{t}")
    return "\n".join(logs)

def process_event(event: Event):
    wfs = Workflow.objects.filter(tenant=event.tenant, is_active=True, trigger=event.name)
    with transaction.atomic():
        event.status = "processing"; event.save(update_fields=["status"])
        for wf in wfs:
            if not _match(wf, event.payload): 
                continue
            run = WorkflowRun.objects.create(tenant=event.tenant, workflow=wf, event=event, status="processing")
            try:
                log = run_actions(wf, event)
                run.status = "done"; run.log = log; run.save(update_fields=["status","log"])
            except Exception as e:
                run.status = "error"; run.log = str(e); run.save(update_fields=["status","log"])
        event.status = "done"; event.save(update_fields=["status"])
