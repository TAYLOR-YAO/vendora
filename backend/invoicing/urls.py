from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import TaxRateViewSet, InvoiceViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'taxrate', TaxRateViewSet, basename='taxrate')
router.register(r'invoice', InvoiceViewSet, basename='invoice')

urlpatterns = [path('', include(router.urls))]
