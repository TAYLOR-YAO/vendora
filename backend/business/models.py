from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from common.models import BaseModel


class Address(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="addresses")

    # core
    line1 = models.CharField(max_length=200)
    line2 = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80, blank=True, null=True)
    postal_code = models.CharField(max_length=24, blank=True, null=True)
    country = models.CharField(max_length=2, default="TG")

    # geo
    lat = models.FloatField(blank=True, null=True)
    lng = models.FloatField(blank=True, null=True)
    place_id = models.CharField(max_length=120, blank=True, null=True)  # external ref (Gmaps, etc.)

    # flags
    is_primary = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "city", "country"]),
            models.Index(fields=["tenant", "is_primary"]),
        ]


class Business(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="businesses")

    # storefront
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=140, unique=True)  # globally unique for marketing URLs
    description = models.TextField(blank=True, null=True)

    # visibility & status
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)  # public browse switch
    status = models.CharField(max_length=20, default="active")  # active, suspended, draft
    published_at = models.DateTimeField(blank=True, null=True)

    # commerce settings
    currency = models.CharField(max_length=3, default="XOF")
    allow_backorder = models.BooleanField(default=False)
    timezone = models.CharField(max_length=64, default="UTC")
    default_language = models.CharField(max_length=8, default="en")

    # media / branding
    logo_url = models.URLField(blank=True, null=True)
    banner_url = models.URLField(blank=True, null=True)

    # contacts / social
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    social_json = models.JSONField(default=dict, blank=True)  # {instagram:…, facebook:…}

    # misc settings / SEO
    settings_json = models.JSONField(default=dict, blank=True)
    seo_json = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "is_public", "is_active", "-created_at"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["name"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "business"
            cand = base
            i = 1
            while Business.objects.filter(slug=cand).exclude(pk=self.pk).exists():
                i += 1
                cand = f"{base}-{i}"
            self.slug = cand
        if self.is_public and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class Store(BaseModel):
    TYPE_CHOICES = (
        ("store", "Store"),
        ("office", "Office"),
        ("pickup", "Pickup Center"),
        ("warehouse", "Warehouse"),
    )

    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="stores")
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE, related_name="stores")

    # identity
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=140)  # unique per business
    type = models.CharField(max_length=32, choices=TYPE_CHOICES, default="store")
    code = models.CharField(max_length=40, blank=True, null=True)  # internal code

    # location
    address = models.ForeignKey("business.Address", on_delete=models.SET_NULL, blank=True, null=True)

    # contacts & hours
    phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    hours_json = models.JSONField(default=dict, blank=True)  # {"mon":{"open":"09:00","close":"18:00"}, ...}

    # visibility
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)
    status = models.CharField(max_length=20, default="active")
    is_default = models.BooleanField(default=False)

    manager_user_id = models.UUIDField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "business", "is_public", "is_active"]),
            models.Index(fields=["business", "slug"]),
            models.Index(fields=["tenant", "code"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["business", "slug"], name="uniq_store_slug_per_business"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "store"
            cand = base
            i = 1
            while Store.objects.filter(business=self.business, slug=cand).exclude(pk=self.pk).exists():
                i += 1
                cand = f"{base}-{i}"
            self.slug = cand
        super().save(*args, **kwargs)
