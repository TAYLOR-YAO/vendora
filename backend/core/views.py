from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, mixins
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import FeatureFlag, PublicConfig, Announcement
from .serializers import (
    FeatureFlagSerializer, PublicConfigSerializer, AnnouncementSerializer
)

# --- Tiny public endpoints ----------------------------------------------------

def healthz(_request):
    return JsonResponse({"ok": True})

class VersionView(APIView):
    permission_classes = [AllowAny]

    def get(self, _):
        version = getattr(settings, "VERSION", None) or getattr(settings, "RELEASE", None) or "dev"
        return Response({
            "ok": True,
            "version": str(version),
            "debug": bool(settings.DEBUG),
            "time": timezone.now().isoformat(),
        })


class TimeView(APIView):
    permission_classes = [AllowAny]

    def get(self, _):
        return Response({"server_time": timezone.now().isoformat()})


class IPView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        ip = request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR")
        return Response({"ip": ip})


class EchoView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Echo back safe headers/body to help debug CORS/proxies
        safe_headers = {
            k: v for k, v in request.headers.items()
            if k.lower() in ("authorization", "content-type", "origin", "referer", "user-agent")
        }
        return Response({
            "method": request.method,
            "path": request.path,
            "query": request.GET.dict(),
            "headers": safe_headers,
            "data": request.data,
        })


class WhoAmIView(APIView):
    permission_classes = [AllowAny]  # allow anonymous; returns minimal info

    def get(self, request):
        if request.user.is_authenticated:
            data = {
                "is_authenticated": True,
                "user_id": str(getattr(request.user, "id", "")),
                "email": getattr(request.user, "email", None),
                "full_name": getattr(request.user, "full_name", None),
                "is_staff": bool(getattr(request.user, "is_staff", False)),
            }
        else:
            data = {"is_authenticated": False}
        return Response(data)


# --- Deeper diagnostics -------------------------------------------------------

class DeepHealthView(APIView):
    """
    GET /api/v1/core/deep-health/?db=1&cache=1&celery=1
    Return component statuses. All checks optional.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        check_db = request.query_params.get("db") == "1"
        check_cache = request.query_params.get("cache") == "1"
        check_celery = request.query_params.get("celery") == "1"

        out = {"ok": True, "time": timezone.now().isoformat()}

        if check_db:
            try:
                with connection.cursor() as cur:
                    cur.execute("SELECT 1;")
                    cur.fetchone()
                out["db"] = {"ok": True}
            except Exception as e:
                out["ok"] = False
                out["db"] = {"ok": False, "error": str(e)}

        if check_cache:
            try:
                cache.set("core_healthz_probe", "1", timeout=10)
                v = cache.get("core_healthz_probe")
                out["cache"] = {"ok": v == "1"}
                if v != "1":
                    out["ok"] = False
            except Exception as e:
                out["ok"] = False
                out["cache"] = {"ok": False, "error": str(e)}

        if check_celery:
            try:
                # Optional: only if you wired a ping task
                from aiapp.tasks import ping as ai_ping  # tiny task returning "pong"
                res = ai_ping.delay()
                val = res.get(timeout=5)
                out["celery"] = {"ok": (val == "pong")}
                if val != "pong":
                    out["ok"] = False
            except Exception as e:
                out["ok"] = False
                out["celery"] = {"ok": False, "error": str(e)}

        return Response(out)


# --- Config / Flags / Announcements (CRUD: staff-only for writes) ------------

class FeatureFlagViewSet(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.CreateModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    queryset = FeatureFlag.objects.all().order_by("key")
    serializer_class = FeatureFlagSerializer
    # Anyone can read flags (frontend needs them); staff to mutate
    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        from .permissions import IsStaffOrReadOnly
        return [IsStaffOrReadOnly()]


class PublicConfigViewSet(mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.CreateModelMixin,
                          mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin,
                          viewsets.GenericViewSet):
    queryset = PublicConfig.objects.all().order_by("key")
    serializer_class = PublicConfigSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        from .permissions import IsStaffOrReadOnly
        return [IsStaffOrReadOnly()]


class AnnouncementViewSet(mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.CreateModelMixin,
                          mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin,
                          viewsets.GenericViewSet):
    queryset = Announcement.objects.all().order_by("-created_at")
    serializer_class = AnnouncementSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "active"):
            return [AllowAny()]
        from .permissions import IsStaffOrReadOnly
        return [IsStaffOrReadOnly()]

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def active(self, request):
        now = timezone.now()
        qs = [a for a in self.get_queryset() if a.is_active]
        ser = self.get_serializer(qs, many=True)
        return Response({"count": len(ser.data), "results": ser.data})
