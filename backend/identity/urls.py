from django.urls import path
from .views import RegisterView, GoogleLoginView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth_register"),
    path("google/", GoogleLoginView.as_view(), name="google_login"),
]