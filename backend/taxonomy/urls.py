from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import IndustryViewSet
from .views import CategoryViewSet
from .views import SubcategoryViewSet

router = DefaultRouter()
router.register(r'industry', IndustryViewSet)
router.register(r'category', CategoryViewSet)
router.register(r'subcategory', SubcategoryViewSet)

urlpatterns = [ path('', include(router.urls)) ]