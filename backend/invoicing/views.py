from rest_framework import viewsets
from .models import TaxRate, Invoice
from .serializers import TaxRateSerializer, InvoiceSerializer

class TaxRateViewSet(viewsets.ModelViewSet):
    queryset = TaxRate.objects.all().order_by('-id') if hasattr(TaxRate, 'id') else TaxRate.objects.all()
    serializer_class = TaxRateSerializer

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all().order_by('-id') if hasattr(Invoice, 'id') else Invoice.objects.all()
    serializer_class = InvoiceSerializer
