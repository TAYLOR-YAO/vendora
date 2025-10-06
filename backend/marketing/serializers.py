from rest_framework import serializers
from .models import Segment, Campaign, CampaignVariant, CampaignSend, CampaignEvent


class SegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Segment
        fields = "__all__"
        read_only_fields = ("tenant", "last_refreshed_at", "approx_count", "created_at", "updated_at")


class CampaignVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignVariant
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at")


class CampaignSerializer(serializers.ModelSerializer):
    variants = CampaignVariantSerializer(many=True, required=False)

    class Meta:
        model = Campaign
        fields = "__all__"
        read_only_fields = ("tenant", "started_at", "completed_at", "created_at", "updated_at")

    def create(self, validated_data):
        variants = validated_data.pop("variants", [])
        campaign = Campaign.objects.create(**validated_data)
        for v in variants:
            CampaignVariant.objects.create(tenant=campaign.tenant, campaign=campaign, **v)
        return campaign

    def update(self, instance, validated_data):
        variants = validated_data.pop("variants", None)
        instance = super().update(instance, validated_data)
        if variants is not None:
            keep = []
            for v in variants:
                key = v.get("key")
                obj, _ = CampaignVariant.objects.update_or_create(
                    tenant=instance.tenant, campaign=instance, key=key, defaults=v
                )
                keep.append(obj.id)
            CampaignVariant.objects.filter(campaign=instance).exclude(id__in=keep).delete()
        return instance


class CampaignSendSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignSend
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at")


class CampaignEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignEvent
        fields = "__all__"
        read_only_fields = ("tenant", "created_at")
