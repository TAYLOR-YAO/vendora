# commerce/urls_public.py
from django.urls import path
from .views_public import PublicProductAvailability
urlpatterns = [ path("public/product/<uuid:product_id>/availability/", PublicProductAvailability.as_view()) ]
