from rest_framework import serializers
from .models import ApiClient, OAuthProvider

class ApiClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiClient
        fields = '__all__'

class OAuthProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = OAuthProvider
        fields = '__all__'
