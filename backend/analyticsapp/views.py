from rest_framework import viewsets
from .models import CdpProfile, Event
from .serializers import CdpProfileSerializer, EventSerializer

class CdpProfileViewSet(viewsets.ModelViewSet):
    queryset = CdpProfile.objects.all().order_by('-id') if hasattr(CdpProfile, 'id') else CdpProfile.objects.all()
    serializer_class = CdpProfileSerializer

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().order_by('-id') if hasattr(Event, 'id') else Event.objects.all()
    serializer_class = EventSerializer
