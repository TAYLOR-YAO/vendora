from django.utils.deprecation import MiddlewareMixin
from platformapp.services.audit import log_event

class AuditRequestMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        try:
            user = getattr(request, "user", None)
            tenant = getattr(user, "tenant", None) or getattr(request, "tenant", None)
            if tenant:
                log_event(
                    tenant=tenant,
                    user_id=str(getattr(user, "id", "")) or None,
                    action=f"http:{request.method}",
                    entity="HTTP",
                    entity_id=request.path[:120],
                    meta={"status": response.status_code}
                )
        except Exception:
            pass
        return response
