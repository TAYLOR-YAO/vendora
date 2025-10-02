from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import TaxRateViewSet
from .views import InvoiceViewSet

router = DefaultRouter()
router.register(r'taxrate', TaxRateViewSet)
router.register(r'invoice', InvoiceViewSet)

urlpatterns = [ path('', include(router.urls)) ]