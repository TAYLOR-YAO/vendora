from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from common.models import BaseModel

# Optional taxonomy relations (uncomment if you have them)
# from taxonomy.models import Category, Subcategory, Industry

class Product(BaseModel):
    tenant   = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="products")
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE, related_name="products")

    # storefront
    name        = models.CharField(max_length=200)
    slug        = models.SlugField(max_length=220, unique=True)
    type        = models.CharField(max_length=20, default="physical")  # physical | service | rental
    description = models.TextField(blank=True, null=True)
    details_json = models.JSONField(default=dict, blank=True)

    # visibility & lifecycle
    is_active  = models.BooleanField(default=True)
    is_public  = models.BooleanField(default=True)     # <— public browse switch
    published_at = models.DateTimeField(blank=True, null=True)

    # pricing (default/fallback – per-variant prices override)
    default_price = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    currency      = models.CharField(max_length=3, default="XOF")

    # optional taxonomy (enable if used)
    # industry     = models.ForeignKey(Industry,   on_delete=models.SET_NULL, null=True, blank=True)
    # category     = models.ForeignKey(Category,   on_delete=models.SET_NULL, null=True, blank=True)
    # subcategory  = models.ForeignKey(Subcategory,on_delete=models.SET_NULL, null=True, blank=True)
    brand        = models.CharField(max_length=120, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_public", "is_active", "-created_at"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["name"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "product"
            cand = base
            i = 1
            while Product.objects.filter(slug=cand).exclude(pk=self.pk).exists():
                i += 1
                cand = f"{base}-{i}"
            self.slug = cand
        if self.is_public and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class ProductImage(BaseModel):
    tenant  = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="product_images")
    product = models.ForeignKey("commerce.Product", on_delete=models.CASCADE, related_name="images")
    url      = models.URLField()
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(fields=["product", "position"], name="uniq_productimage_position_per_product"),
        ]


class ProductVideo(BaseModel):
    tenant  = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="product_videos")
    product = models.ForeignKey("commerce.Product", on_delete=models.CASCADE, related_name="videos")
    url      = models.URLField()
    provider = models.CharField(max_length=50, blank=True, null=True)  # youtube, vimeo, file
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(fields=["product", "position"], name="uniq_productvideo_position_per_product"),
        ]


class Variant(BaseModel):
    tenant  = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="variants")
    product = models.ForeignKey("commerce.Product", on_delete=models.CASCADE, related_name="variants")
    sku     = models.CharField(max_length=120)
    price   = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "sku"], name="uniq_sku_per_tenant"),
        ]
        indexes = [
            models.Index(fields=["product", "is_active"]),
            models.Index(fields=["tenant", "sku"]),
        ]


class Cart(BaseModel):
    tenant   = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="carts")
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, null=True, blank=True)
    status   = models.CharField(max_length=16, default="open")  # open | merged | converted | abandoned


class CartItem(BaseModel):
    tenant  = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="cart_items")
    cart    = models.ForeignKey("commerce.Cart", on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("commerce.Variant", on_delete=models.CASCADE)
    qty     = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    price   = models.DecimalField(max_digits=18, decimal_places=2)


class Order(BaseModel):
    tenant   = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="orders")
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE, related_name="orders")
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, null=True, blank=True)
    status   = models.CharField(max_length=20, default="pending")
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    currency     = models.CharField(max_length=3, default="XOF")


class OrderItem(BaseModel):
    tenant  = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="order_items")
    order   = models.ForeignKey("commerce.Order", on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("commerce.Variant", on_delete=models.CASCADE)
    qty     = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    price   = models.DecimalField(max_digits=18, decimal_places=2)


class Review(BaseModel):
    tenant  = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey("commerce.Product", on_delete=models.CASCADE, related_name="reviews")
    rating  = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
