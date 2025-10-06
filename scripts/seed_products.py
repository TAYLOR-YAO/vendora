import os
import sys
import django
import random
from decimal import Decimal

# --- Fix project path ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# --- Set Django settings ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.vendora_backend.settings.dev")
django.setup()

from django.utils import timezone
from uuid import uuid4
from commerce.models import Product, ProductImage, ProductVideo, Variant
from business.models import Business
from platformapp.models import Tenant


def seed_products():
    tenant, _ = Tenant.objects.get_or_create(name="Demo Tenant")
    business, _ = Business.objects.get_or_create(
        tenant=tenant,
        defaults={"name": "Demo Business", "slug": "demo-business"}
    )

    for n in range(3):
        product, created = Product.objects.get_or_create(
            tenant=tenant,
            business=business,
            name=f"Product {n+1}",
            defaults={
                "description": f"Sample product #{n+1} description.",
                "default_price": Decimal(random.uniform(5, 99)).quantize(Decimal("0.01")),
                "currency": "USD",
                "is_active": True,
                "type": "simple",
                "details_json": "{}",
            },
        )

        if created:
            print(f"🛍️ Created {product.name}")
        else:
            print(f"↻ Updating {product.name}")

        # Add or refresh images
        ProductImage.objects.update_or_create(
            product=product,
            tenant=tenant,
            position=0,
            defaults={
                "url": f"https://placehold.co/600x400?text=Product+{n+1}",
                "alt_text": f"Main image for Product {n+1}",
            },
        )

        # Add sample video
        ProductVideo.objects.update_or_create(
            product=product,
            tenant=tenant,
            position=0,
            defaults={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "provider": "youtube",
            },
        )

        # Add a few variants
        for v in range(2):
            Variant.objects.update_or_create(
                product=product,
                tenant=tenant,
                sku=f"SKU-{product.id}-{v+1}",
                defaults={
                    "price": Decimal(random.uniform(10, 150)).quantize(Decimal("0.01")),
                    "is_active": True,
                },
            )

    print("✅ Seed complete — check /api/v1/commerce/product/")

if __name__ == "__main__":
    seed_products()
