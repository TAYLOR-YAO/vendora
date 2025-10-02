from rest_framework import viewsets
from .models import NotificationTemplate, NotificationPreference, NotificationDispatch, NotificationLog
from .serializers import NotificationTemplateSerializer, NotificationPreferenceSerializer, NotificationDispatchSerializer, NotificationLogSerializer

class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.all().order_by('-id') if hasattr(NotificationTemplate, 'id') else NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer

class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    queryset = NotificationPreference.objects.all().order_by('-id') if hasattr(NotificationPreference, 'id') else NotificationPreference.objects.all()
    serializer_class = NotificationPreferenceSerializer

class NotificationDispatchViewSet(viewsets.ModelViewSet):
    queryset = NotificationDispatch.objects.all().order_by('-id') if hasattr(NotificationDispatch, 'id') else NotificationDispatch.objects.all()
    serializer_class = NotificationDispatchSerializer

class NotificationLogViewSet(viewsets.ModelViewSet):
    queryset = NotificationLog.objects.all().order_by('-id') if hasattr(NotificationLog, 'id') else NotificationLog.objects.all()
    serializer_class = NotificationLogSerializer
