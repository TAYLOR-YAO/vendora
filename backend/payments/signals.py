from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment
from notificationsapp.utils import queue_notification

@receiver(post_save, sender=Payment)
def on_payment_status_change(sender, instance: Payment, created, **kwargs):
    if instance.status == "succeeded":
        order = instance.order
        if getattr(order, "status", None) != "paid":
            order.status = "paid"
            order.save(update_fields=["status"])
            queue_notification(
                tenant=order.tenant,
                channel="email",
                payload={"type":"order_paid","order_id":str(order.id)}
            )
