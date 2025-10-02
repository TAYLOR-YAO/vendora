from rest_framework import viewsets
from .models import Segment, Campaign
from .serializers import SegmentSerializer, CampaignSerializer

class SegmentViewSet(viewsets.ModelViewSet):
    queryset = Segment.objects.all().order_by('-id') if hasattr(Segment, 'id') else Segment.objects.all()
    serializer_class = SegmentSerializer

class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all().order_by('-id') if hasattr(Campaign, 'id') else Campaign.objects.all()
    serializer_class = CampaignSerializer
