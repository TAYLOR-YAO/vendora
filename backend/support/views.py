from rest_framework import viewsets
from .models import Ticket, KBArticle
from .serializers import TicketSerializer, KBArticleSerializer

class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all().order_by('-id') if hasattr(Ticket, 'id') else Ticket.objects.all()
    serializer_class = TicketSerializer

class KBArticleViewSet(viewsets.ModelViewSet):
    queryset = KBArticle.objects.all().order_by('-id') if hasattr(KBArticle, 'id') else KBArticle.objects.all()
    serializer_class = KBArticleSerializer
