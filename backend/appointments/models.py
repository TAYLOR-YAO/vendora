from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant
from crm.models import Customer

class Resource(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="resources")
    type = models.CharField(max_length=20, default="staff")
    name = models.CharField(max_length=200)

class Booking(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="bookings")
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="bookings")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="bookings")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(max_length=20, default="booked")
