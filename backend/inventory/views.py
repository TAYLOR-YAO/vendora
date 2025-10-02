from rest_framework import viewsets
from .models import Warehouse, StockItem, StockLedger
from .serializers import WarehouseSerializer, StockItemSerializer, StockLedgerSerializer

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all().order_by('-id') if hasattr(Warehouse, 'id') else Warehouse.objects.all()
    serializer_class = WarehouseSerializer

class StockItemViewSet(viewsets.ModelViewSet):
    queryset = StockItem.objects.all().order_by('-id') if hasattr(StockItem, 'id') else StockItem.objects.all()
    serializer_class = StockItemSerializer

class StockLedgerViewSet(viewsets.ModelViewSet):
    queryset = StockLedger.objects.all().order_by('-id') if hasattr(StockLedger, 'id') else StockLedger.objects.all()
    serializer_class = StockLedgerSerializer
