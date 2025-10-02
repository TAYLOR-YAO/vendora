from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant
from crm.models import Customer

class Ticket(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="tickets")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=200)
    status = models.CharField(max_length=16, default="open")
    priority = models.CharField(max_length=16, default="medium")

class KBArticle(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="kb_articles")
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_published = models.BooleanField(default=False)
