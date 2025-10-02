from rest_framework import viewsets
from .models import Address, Business, Store
from .serializers import AddressSerializer, BusinessSerializer, StoreSerializer

class AddressViewSet(viewsets.ModelViewSet):
    queryset = Address.objects.all().order_by('-id') if hasattr(Address, 'id') else Address.objects.all()
    serializer_class = AddressSerializer

class BusinessViewSet(viewsets.ModelViewSet):
    queryset = Business.objects.all().order_by('-id') if hasattr(Business, 'id') else Business.objects.all()
    serializer_class = BusinessSerializer

class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all().order_by('-id') if hasattr(Store, 'id') else Store.objects.all()
    serializer_class = StoreSerializer
