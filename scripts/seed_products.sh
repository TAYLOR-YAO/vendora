#!/usr/bin/env bash
set -euo pipefail

# This script seeds sample products using the Django shell.
# It's designed to be run from the project root directory.

echo "🌱 Starting product seeding..."

# Use the venv python if available, otherwise fall back to system python
PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="python"

# Ensure we are in the project root where backend/manage.py exists
if [ ! -f "backend/manage.py" ]; then
    echo "❌ Error: This script must be run from the project root directory."
    exit 1
fi

$PYTHON_BIN backend/manage.py shell <<'PY'
import random
from decimal import Decimal
from commerce.models import Product, ProductImage, ProductVideo, Variant
from business.models import Business
from platformapp.models import Tenant

tenant, _ = Tenant.objects.get_or_create(slug="demo", defaults={"name": "Demo Tenant"})
business, _ = Business.objects.get_or_create(
    tenant=tenant,
    url_slug="demo-business",
    defaults={"name": "Demo Business"}
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
            "details_json": {},
        },
    )

    if created:
        print(f"🛍️  Created {product.name}")
    else:
        print(f"🔄  Updating {product.name}")

    ProductImage.objects.update_or_create(product=product, tenant=tenant, position=0, defaults={"url": f"https://placehold.co/600x400?text=Product+{n+1}", "alt_text": f"Main image for Product {n+1}"})
    ProductVideo.objects.update_or_create(product=product, tenant=tenant, position=0, defaults={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "provider": "youtube"})

    for v in range(2):
        Variant.objects.update_or_create(product=product, tenant=tenant, sku=f"SKU-{product.id}-{v+1}", defaults={"price": Decimal(random.uniform(10, 150)).quantize(Decimal("0.01")), "is_active": True})

print("\n✅ Seed complete — check /api/v1/commerce/product/")
PY

echo "🚀 Seeding script finished."