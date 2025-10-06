from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    CustomerViewSet, ContactViewSet, PipelineViewSet,
    OpportunityViewSet, ActivityViewSet, LeadIntakeAPIView
)

router = DefaultRouter()  # default trailing slash = True
router.register(r'customer', CustomerViewSet, basename="customer")
router.register(r'contact', ContactViewSet, basename="contact")
router.register(r'pipeline', PipelineViewSet, basename="pipeline")
router.register(r'opportunity', OpportunityViewSet, basename="opportunity")
router.register(r'activity', ActivityViewSet, basename="activity")

urlpatterns = [
    path('', include(router.urls)),

    # Public, rate-limited intake
    path('public/lead/', LeadIntakeAPIView.as_view(), name="crm_public_lead"),
]
