from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from business.models import Business
from commerce.models import Product
from commerce.serializers import ProductSerializer
from platformapp.models import Tenant


class Command(BaseCommand):
    help = "Seeds a sample product with multiple variants and images using the ProductSerializer."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Starting product seeding...")

        # 1. Get or create a Tenant and Business to associate the product with.
        tenant, t_created = Tenant.objects.get_or_create(
            slug="demo",
            defaults={"name": "Demo Tenant", "status": "active"},
        )
        if t_created:
            self.stdout.write(self.style.SUCCESS(f"Created tenant: {tenant.name}"))

        business, b_created = Business.objects.get_or_create(
            tenant=tenant,
            url_slug="demo-biz",
            defaults={"name": "Demo Business", "currency": "XOF"},
        )
        if b_created:
            self.stdout.write(self.style.SUCCESS(f"Created business: {business.name}"))

        # 2. Define the complete product data, including nested images and variants.
        product_data = {
            "tenant": str(tenant.id),
            "business": str(business.id),
            "name": "Premium Hoodie",
            "type": "physical",
            "default_price": "25000.00",
            "currency": "XOF",
            "is_active": True,
            "description": "A comfortable and stylish hoodie, perfect for any occasion.",
            "details_json": {"material": "80% cotton, 20% polyester", "origin": "Togo"},
            "images": [
                {
                    "url": "https://picsum.photos/seed/hoodie1/800/800",
                    "alt_text": "Front view of the Premium Hoodie in charcoal",
                    "position": 0,
                },
                {
                    "url": "https://picsum.photos/seed/hoodie2/800/800",
                    "alt_text": "Back view of the Premium Hoodie in charcoal",
                    "position": 1,
                },
            ],
            "variants": [
                {"sku": "HOODIE-CH-S", "price": "25000.00", "is_active": True},
                {"sku": "HOODIE-CH-M", "price": "25000.00", "is_active": True},
                {"sku": "HOODIE-CH-L", "price": "26000.00", "is_active": True},
                {"sku": "HOODIE-NV-M", "price": "25000.00", "is_active": False},
            ],
        }

        # 3. Use the serializer to create the product and its children.
        self.stdout.write(f"Creating product '{product_data['name']}'...")
        serializer = ProductSerializer(data=product_data)

        if not serializer.is_valid():
            self.stderr.write(self.style.ERROR("Validation failed!"))
            self.stderr.write(str(serializer.errors))
            raise CommandError("Could not seed product due to validation errors.")

        product = serializer.save()

        self.stdout.write(self.style.SUCCESS("\nSeeding complete! ✅"))
        self.stdout.write(f"  - Product created: '{product.name}' (ID: {product.id})")
        self.stdout.write(f"  - Variants created: {product.variants.count()}")
        self.stdout.write(f"  - Images created: {product.images.count()}")