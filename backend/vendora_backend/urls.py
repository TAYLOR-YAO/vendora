from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse, HttpResponse
from django.views.generic import RedirectView
from django.utils.translation import gettext_lazy as _

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['full_name'] = getattr(user, 'full_name', '')
        return token

# ⬇️ Add CORS-safe subclasses that implement .options()
class TokenObtainPairCORSView(TokenObtainPairView):
    def options(self, request, *args, **kwargs):
        # 204 is a common/no-body preflight response
        return HttpResponse(status=204)

class TokenRefreshCORSView(TokenRefreshView):
    def options(self, request, *args, **kwargs):
        return HttpResponse(status=204)


def root(_r):
    return JsonResponse({
        "service": _("vendora-backend"),
        "docs": _("/api/docs"),
        "health": _("/api/v1/core/healthz/"),
    })


urlpatterns = [
    path("admin", RedirectView.as_view(url="/admin/", permanent=False)),  # <— add this
    path("admin/", admin.site.urls),

    # API docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),

    # App routers
    path("api/v1/search/", include("searchapp.urls")),
    path("api/v1/billing/", include("billing.urls")),
    path("api/v1/core/", include("core.urls")),
    path("api/v1/platform/", include("platformapp.urls")),
    path("api/v1/identity/", include("identity.urls")),
    path("api/v1/taxonomy/", include("taxonomy.urls")),
    path("api/v1/business/", include("business.urls")),
    path("api/v1/crm/", include("crm.urls")),
    path("api/v1/commerce/", include("commerce.urls")),
    path("api/v1/payments/", include("payments.urls")),
    path("api/v1/inventory/", include("inventory.urls")),
    path("api/v1/shipments/", include("shipments.urls")),
    path("api/v1/hr/", include("hr.urls")),
    path("api/v1/invoicing/", include("invoicing.urls")),
    path("api/v1/appointments/", include("appointments.urls")),
    path("api/v1/notifications/", include("notificationsapp.urls")),
    path("api/v1/support/", include("support.urls")),
    path("api/v1/marketing/", include("marketing.urls")),
    path("api/v1/analytics/", include("analyticsapp.urls")),
    path("api/v1/ai/", include("aiapp.urls")),

    # SimpleJWT (now OPTIONS-safe)
    path(
        "api/token/",
        TokenObtainPairCORSView.as_view(serializer_class=MyTokenObtainPairSerializer),
        name="token_obtain_pair",
    ),
    path("api/token/refresh/", TokenRefreshCORSView.as_view(), name="token_refresh"),
    path("api/token/verify/", TokenVerifyView.as_view(), name="token_verify"),

    # dj-rest-auth (optional; unrelated to SimpleJWT flow)
    #path("dj-rest-auth/", include("dj_rest_auth.urls")),
    #path("dj-rest-auth/registration/", include("dj_rest_auth.registration.urls")),

    # Put root last
    path("", root),
]
