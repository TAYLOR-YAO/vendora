from rest_framework import viewsets
from .models import ApiClient, OAuthProvider
from .serializers import ApiClientSerializer, OAuthProviderSerializer

class ApiClientViewSet(viewsets.ModelViewSet):
    queryset = ApiClient.objects.all().order_by('-id') if hasattr(ApiClient, 'id') else ApiClient.objects.all()
    serializer_class = ApiClientSerializer

class OAuthProviderViewSet(viewsets.ModelViewSet):
    queryset = OAuthProvider.objects.all().order_by('-id') if hasattr(OAuthProvider, 'id') else OAuthProvider.objects.all()
    serializer_class = OAuthProviderSerializer
