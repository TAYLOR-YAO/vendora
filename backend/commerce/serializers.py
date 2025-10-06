from rest_framework import serializers
from django.db import transaction
from .models import (
    Product, Variant, Cart, CartItem, Order, OrderItem, Review,
    ProductImage, ProductVideo
)

# ---------- Children (write-safe; tenant/product injected server-side) ----------
class ProductImageSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    class Meta:
        model = ProductImage
        exclude = ("product", "tenant")
        read_only_fields = ("created_at", "updated_at")

class ProductVideoSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    class Meta:
        model = ProductVideo
        exclude = ("product", "tenant")
        read_only_fields = ("created_at", "updated_at")

class VariantSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    class Meta:
        model = Variant
        exclude = ("product", "tenant")
        read_only_fields = ("created_at", "updated_at")

# ---------- LIST serializer (fast, compact) ----------
class ProductListSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()
    min_price     = serializers.SerializerMethodField()
    max_price     = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id", "name", "slug", "type", "is_public", "is_active",
            "default_price", "currency", "primary_image", "min_price", "max_price",
            "created_at", "updated_at",
        )

    def get_primary_image(self, obj):
        img = obj.images.first()
        return img.url if img else None

    def get_min_price(self, obj):
        prices = [v.price for v in obj.variants.all() if v.price is not None]
        if not prices and obj.default_price is not None:
            prices = [obj.default_price]
        return min(prices) if prices else None

    def get_max_price(self, obj):
        prices = [v.price for v in obj.variants.all() if v.price is not None]
        if not prices and obj.default_price is not None:
            prices = [obj.default_price]
        return max(prices) if prices else None

# ---------- DETAIL/WRITE serializer (nested) ----------
class ProductDetailSerializer(serializers.ModelSerializer):
    images   = ProductImageSerializer(many=True, required=False)
    videos   = ProductVideoSerializer(many=True, required=False)
    variants = VariantSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ("tenant", "business", "created_at", "updated_at", "slug", "published_at")

    @transaction.atomic
    def create(self, validated_data):
        images_data   = validated_data.pop("images", [])
        variants_data = validated_data.pop("variants", [])
        videos_data   = validated_data.pop("videos", [])
        product = Product.objects.create(**validated_data)

        for i, img in enumerate(images_data):
            ProductImage.objects.create(product=product, tenant=product.tenant,
                                        position=img.get("position", i), **{k:v for k,v in img.items() if k not in ("position",)})
        for i, vid in enumerate(videos_data):
            ProductVideo.objects.create(product=product, tenant=product.tenant,
                                        position=vid.get("position", i), **{k:v for k,v in vid.items() if k not in ("position",)})
        for var in variants_data:
            Variant.objects.create(product=product, tenant=product.tenant, **var)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        images_data   = validated_data.pop("images", None)
        variants_data = validated_data.pop("variants", None)
        videos_data   = validated_data.pop("videos", None)
        instance = super().update(instance, validated_data)

        def upsert(manager, child_model, data_list):
            if data_list is None:
                return
            existing = {str(o.id): o for o in manager.all()}
            keep = set()
            for payload in data_list:
                obj_id = str(payload.pop("id", "")) if "id" in payload else ""
                if obj_id and obj_id in existing:
                    obj = existing[obj_id]
                    for k, v in payload.items():
                        setattr(obj, k, v)
                    obj.save(update_fields=list(payload.keys()))
                    keep.add(obj_id)
                else:
                    created = child_model.objects.create(product=instance, tenant=instance.tenant, **payload)
                    keep.add(str(created.id))
            child_model.objects.filter(product=instance).exclude(id__in=keep).delete()

        upsert(instance.images, ProductImage, images_data)
        upsert(instance.videos, ProductVideo, videos_data)
        upsert(instance.variants, Variant, variants_data)
        return instance

# ---------- Other serializers ----------
class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = "__all__"

class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = "__all__"

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = "__all__"

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        fields = "__all__"

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = "__all__"
