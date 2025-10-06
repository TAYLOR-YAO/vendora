from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Employee, OnboardingTask

@receiver(post_save, sender=Employee)
def create_default_onboarding(sender, instance: Employee, created, **kwargs):
    if created:
        OnboardingTask.objects.create(
            tenant=instance.tenant,
            employee=instance,
            title="Welcome pack",
            status="open",
        )
        OnboardingTask.objects.create(
            tenant=instance.tenant,
            employee=instance,
            title="Account setup",
            status="open",
        )
