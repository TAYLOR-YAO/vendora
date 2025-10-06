from django.db import models
from common.models import BaseModel
class Industry(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="industries")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)
class Category(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="categories")
    industry = models.ForeignKey("taxonomy.Industry", on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)
class Subcategory(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="subcategories")
    category = models.ForeignKey("taxonomy.Category", on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)
