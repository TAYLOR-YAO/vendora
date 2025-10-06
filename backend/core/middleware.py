from django.http import HttpResponse
from django.conf import settings
import time, uuid

ALLOWED_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
ALLOWED_HEADERS = "authorization, content-type, accept"

class DevCORSPreflightMiddleware:
    """
    DEBUG-only safety net for Cloud Shell: short-circuit every OPTIONS request
    with CORS headers so the browser never sees 404/302 on preflight.
    Keep this BEFORE CommonMiddleware in settings.MIDDLEWARE.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEBUG and request.method == "OPTIONS":
            origin = request.META.get("HTTP_ORIGIN", "*")
            resp = HttpResponse(status=204)
            resp["Access-Control-Allow-Origin"] = origin
            resp["Vary"] = "Origin"
            resp["Access-Control-Allow-Methods"] = ALLOWED_METHODS
            resp["Access-Control-Allow-Headers"] = ALLOWED_HEADERS
            resp["Access-Control-Max-Age"] = "600"
            return resp
        return self.get_response(request)


class RequestIDMiddleware:
    """
    Adds/propagates a request id for tracing. Accessible in logs and responses.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        rid = request.META.get("HTTP_X_REQUEST_ID") or str(uuid.uuid4())
        request.request_id = rid
        response = self.get_response(request)
        response["X-Request-ID"] = rid
        return response


class TimingMiddleware:
    """
    Adds X-Response-Time-ms for quick perf inspection.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        t0 = time.perf_counter()
        resp = self.get_response(request)
        dt = int((time.perf_counter() - t0) * 1000)
        resp["X-Response-Time-ms"] = str(dt)
        return resp
