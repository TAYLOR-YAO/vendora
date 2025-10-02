from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant
from business.models import Business
from crm.models import Customer

class Product(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="products")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, default="physical")  # physical, service, rental
    default_price = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="XOF")
    is_active = models.BooleanField(default=True)

class Variant(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="variants")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=120, unique=True)
    price = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

class Cart(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="carts")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=16, default="open")

class CartItem(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="cart_items")
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    qty = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=18, decimal_places=2)

class Order(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="orders")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="orders")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default="pending")
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="XOF")

class OrderItem(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="order_items")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    qty = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=18, decimal_places=2)

class Review(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(default=5)
    comment = models.TextField(blank=True, null=True)
