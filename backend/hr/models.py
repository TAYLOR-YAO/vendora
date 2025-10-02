from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant
from business.models import Business, Store

class Employee(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="employees")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="employees")
    store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)
    status = models.CharField(max_length=20, default="active")
