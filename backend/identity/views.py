from django.contrib.auth import get_user_model
from rest_framework import generics
from rest_framework.permissions import AllowAny
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

from .serializers import UserSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    API endpoint for user registration.
    """
    queryset = User.objects.all()
    permission_classes = (AllowAny,) # Allow any user (authenticated or not) to access this endpoint.
    serializer_class = UserSerializer


class GoogleLoginView(SocialLoginView):
    """
    API endpoint for Google social login.
    """
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client