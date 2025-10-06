# This file was auto-generated as a scaffold.
# SAFE to edit. Keep functions/class names if you rely on them across apps.

from django.db.models.signals import post_save
from django.dispatch import receiver

# Example signal:
# from .models import ModelName
# from .notifications import Notification, send
#
# @receiver(post_save, sender=ModelName)
# def on_modelname_saved(sender, instance, created, **kwargs):
#     subject = f"ModelName {'created' if created else 'updated'}: {instance.pk}"
#     send(Notification(subject=subject, message=str(instance)))
