from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import WarehouseViewSet
from .views import StockItemViewSet
from .views import StockLedgerViewSet
from .views import StockReservationViewSet

router = DefaultRouter()
router.register(r'warehouse', WarehouseViewSet)
router.register(r'stockitem', StockItemViewSet)
router.register(r'stockledger', StockLedgerViewSet)
router.register(r'stockreservation', StockReservationViewSet)

urlpatterns = [ path('', include(router.urls)) ]