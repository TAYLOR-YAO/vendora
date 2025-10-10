# File: backend/vendora_backend/urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse, HttpResponse
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerSplitView
from rest_framework.renderers import TemplateHTMLRenderer, StaticHTMLRenderer

from .api_router import router as api_v1_router
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from vendora_backend.ping_view import ping
from django.views.decorators.csrf import ensure_csrf_cookie

def root(_r):
    return JsonResponse({
        "service": "vendora-backend",
        "docs": "/api/docs",
        "health": "/api/v1/core/healthz/",
    })

def csrf_ok(_request):
    return JsonResponse({"ok": True})

urlpatterns = [
    path("ping/", ping),
    path("admin", RedirectView.as_view(url="/admin/", permanent=False)),
    path("admin/", admin.site.urls),
    path("auth/csrf/", ensure_csrf_cookie(csrf_ok), name="auth_csrf"),

    # API docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),    
    path("api/docs/", SpectacularSwaggerSplitView.as_view(
        url_name="schema",
        renderer_classes=[TemplateHTMLRenderer, StaticHTMLRenderer]
    ), name="swagger-ui"),

    # Feature routers
    path("api/v1/core/", include("core.urls")),
    path("api/v1/platform/", include("platformapp.urls")),
    path("api/v1/identity/", include("identity.urls")),  # optional, if you expose identity features under api too

    # Auto-generated tenant-scoped APIs for all business apps
    path("api/v1/", include(api_v1_router.urls)),

    # 🔐 Identity (clean surface for frontend)
    path("auth/", include(("identity.urls", "identity"), namespace="auth")),

    # (Optional) Keep dj-rest-auth and registration endpoints (JWT flow)
    # path("dj-rest-auth/", include("dj_rest_auth.urls")),
    # path("dj-rest-auth/registration/", include("dj_rest_auth.registration.urls")),

    # SimpleJWT
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/verify/", TokenVerifyView.as_view(), name="token_verify"),

    path("", root),
]
