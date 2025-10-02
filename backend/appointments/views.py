from rest_framework import viewsets
from .models import Resource, Booking
from .serializers import ResourceSerializer, BookingSerializer

class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all().order_by('-id') if hasattr(Resource, 'id') else Resource.objects.all()
    serializer_class = ResourceSerializer

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all().order_by('-id') if hasattr(Booking, 'id') else Booking.objects.all()
    serializer_class = BookingSerializer
