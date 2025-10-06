from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Booking
from notificationsapp.utils import queue_notification
from datetime import timedelta

REMINDER_MIN_BEFORE = 60  # 1 hour before start

@receiver(post_save, sender=Booking)
def on_booking_created(sender, instance: Booking, created, **kwargs):
    if not created:
        return
    # Queue confirmation (email or SMS) — adjust channel/to_address as needed
    queue_notification(
        tenant=instance.tenant,
        template_id=None,  # or resolve a template per tenant like "booking_confirmed"
        topic_id=None,
        to_user_id=getattr(instance.customer, "id", None),
        to_address=None,  # put customer's email/phone if you store it
        channel="email",
        payload={
            "resource": instance.resource.name,
            "service": getattr(instance.service, "name", ""),
            "start_at": instance.start_at.isoformat(),
        },
    )
    # Reminder (scheduled)
    remind_at = instance.start_at - timedelta(minutes=REMINDER_MIN_BEFORE)
    if remind_at > timezone.now():
        queue_notification(
            tenant=instance.tenant,
            template_id=None,  # e.g., "booking_reminder"
            to_user_id=getattr(instance.customer, "id", None),
            channel="email",
            payload={
                "service": getattr(instance.service, "name", ""),
                "start_at": instance.start_at.isoformat(),
            },
            schedule_at=remind_at.isoformat(),
        )
