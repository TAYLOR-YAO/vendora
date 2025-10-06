from django.db import models
from common.models import BaseModel
class Ticket(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="tickets")
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=200)
    status = models.CharField(max_length=16, default="open")
    priority = models.CharField(max_length=16, default="medium")
class KBArticle(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="kb_articles")
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_published = models.BooleanField(default=False)
