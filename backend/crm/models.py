from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant

class Customer(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="customers")
    type = models.CharField(max_length=20, default="person")
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)

class Contact(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="contacts")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True, related_name="contacts")
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)

class Pipeline(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="pipelines")
    name = models.CharField(max_length=120)

class Opportunity(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="opportunities")
    pipeline = models.ForeignKey(Pipeline, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    stage = models.CharField(max_length=32, default="new")
    owner_user_id = models.UUIDField(blank=True, null=True)

class Activity(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="activities")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    kind = models.CharField(max_length=20, default="note")  # note, call, email
    content = models.TextField(blank=True, null=True)
