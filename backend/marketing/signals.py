from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Campaign

@receiver(post_save, sender=Campaign)
def on_campaign_updated(sender, instance: Campaign, created, **kwargs):
    # Hook to enqueue scheduled jobs (Celery beat scanning for scheduled campaigns is cleaner).
    pass
