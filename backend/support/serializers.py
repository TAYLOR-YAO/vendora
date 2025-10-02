from rest_framework import serializers
from .models import Ticket, KBArticle

class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = '__all__'

class KBArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = KBArticle
        fields = '__all__'
