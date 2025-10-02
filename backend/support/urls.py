from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import TicketViewSet
from .views import KBArticleViewSet

router = DefaultRouter()
router.register(r'ticket', TicketViewSet)
router.register(r'kbarticle', KBArticleViewSet)

urlpatterns = [ path('', include(router.urls)) ]