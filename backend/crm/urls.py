from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import CustomerViewSet
from .views import ContactViewSet
from .views import PipelineViewSet
from .views import OpportunityViewSet
from .views import ActivityViewSet

router = DefaultRouter()
router.register(r'customer', CustomerViewSet)
router.register(r'contact', ContactViewSet)
router.register(r'pipeline', PipelineViewSet)
router.register(r'opportunity', OpportunityViewSet)
router.register(r'activity', ActivityViewSet)

urlpatterns = [ path('', include(router.urls)) ]