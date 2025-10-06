# backend/business/serializers.py
from __future__ import annotations

from rest_framework import serializers
from .models import Address, Business, Store


# ---------- Address ----------
class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at")


# ---------- Business ----------
class BusinessListSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Business
        fields = (
            "id",
            "name",
            "slug",        # use url_slug here if your model uses that name
            "logo_url",    # remove if not on the model
            "banner_url",  # remove if not on the model
            "is_public",   # remove if not on the model
            "is_active",   # remove if not on the model
            "currency",
            "display_name",
            "created_at",
            "updated_at",
        )

    def get_display_name(self, obj: Business) -> str:
        return getattr(obj, "name", "")


class BusinessDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = "__all__"
        read_only_fields = (
            "tenant",
            "published_at",  # remove if not on the model
            "created_at",
            "updated_at",
            "slug",          # if slug is auto/managed server-side
        )


# Backwards-compat alias
class BusinessSerializer(BusinessDetailSerializer):
    """Alias so old imports keep working."""
    pass


# ---------- Store ----------
class StoreListSerializer(serializers.ModelSerializer):
    address_summary = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Store
        fields = (
            "id",
            "name",
            "slug",
            "type",
            "is_public",   # remove if not on the model
            "is_active",   # remove if not on the model
            "address_summary",
            "created_at",
            "updated_at",
        )

    def get_address_summary(self, obj: Store) -> str | None:
        a = getattr(obj, "address", None)
        if not a:
            return None
        parts = [a.line1, a.city, a.country]
        return ", ".join(p for p in parts if p)


class StoreDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at", "slug")


# Backwards-compat alias
class StoreSerializer(StoreDetailSerializer):
    """Alias so old imports keep working."""
    pass


__all__ = [
    "AddressSerializer",
    "BusinessListSerializer",
    "BusinessDetailSerializer",
    "BusinessSerializer",   # legacy name
    "StoreListSerializer",
    "StoreDetailSerializer",
    "StoreSerializer",      # legacy name
]
