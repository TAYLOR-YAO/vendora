from django.utils import timezone
from datetime import timedelta
from vendora_backend.celery import app
from .models import Subscription
from invoicing.models import Invoice

@app.task
def generate_cycle_invoices():
    now = timezone.now()
    subs = Subscription.objects.filter(status="active", current_period_end__lte=now)
    for s in subs.select_related("plan"):
        amount = 0
        # Use your pricing logic (seats * price, plus usage)
        price = s.plan.prices.first()
        if price and price.mode == "per_seat":
            amount = (price.amount or 0) * s.seats
        # TODO: add usage charges from UsageRecord
        Invoice.objects.create(
            tenant=s.tenant,
            order=None,  # billing invoices independent of commerce orders
            number=f"SUB-{s.id}-{now:%Y%m}",
            total_amount=amount,
            currency=price.currency if price else "XOF",
            status="open",
        )
        # roll period
        s.current_period_start = now
        s.current_period_end = now + timedelta(days=30)
        s.save(update_fields=["current_period_start","current_period_end"])
