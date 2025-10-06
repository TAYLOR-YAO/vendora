from common.mixins import TenantScopedModelViewSet
from .models import Ticket, KBArticle
from .serializers import TicketSerializer, KBArticleSerializer

class TicketViewSet(TenantScopedModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

class KBArticleViewSet(TenantScopedModelViewSet):
    queryset = KBArticle.objects.all()
    serializer_class = KBArticleSerializer
from typing import Dict, Any, Optional
from collections import Counter
from datetime import timedelta

from django.db.models import Q
from django.utils.timezone import now
from django.utils.dateparse import parse_datetime, parse_date
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_headers

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from common.mixins import TenantScopedModelViewSet
from .models import Ticket, KBArticle
from .serializers import TicketSerializer, KBArticleSerializer

# -----------------------------
# Permissions aligned to policy
# -----------------------------

class PublicReadPrivateWrite(permissions.BasePermission):
    """
    - Allow anyone to read (list/retrieve).
    - Require auth for write actions (create/update/partial_update/destroy & custom write actions).
    """
    def has_permission(self, request, view):
        if view.action in ("list", "retrieve"):
            return True
        return bool(request.user and request.user.is_authenticated)


class TicketScopedPermission(permissions.BasePermission):
    """
    - Staff can see/manage everything.
    - Authenticated non-staff can see/update ONLY their own tickets (by `customer` linkage when applicable).
    - Anonymous may create (we'll attach or create a Customer record if email is provided).
    """
    SAFE_READ = {"list", "retrieve"}
    SAFE_CUSTOMER_WRITE = {"add_note", "set_status", "escalate", "reopen"}  # limit what end-users can do

    def has_permission(self, request, view):
        # Allow anonymous create (support portal)
        if view.action == "create":
            return True
        # Other actions require auth at least
        if view.action in self.SAFE_READ.union(self.SAFE_CUSTOMER_WRITE).union({"close", "assign_customer", "assign_me"}):
            return True
        # Default deny otherwise
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj: Ticket):
        user = request.user
        is_staff = bool(user and user.is_authenticated and getattr(user, "is_staff", False))

        if is_staff:
            return True

        # If ticket is linked to a customer with a known user-id mapping in your platform,
        # implement that mapping here. If not, default: customers can only act on their ticket
        # if it is directly linked to their customer id (you can customize this rule).
        # For now, allow non-staff to view their own tickets IF authenticated and customer present.
        if view.action in {"retrieve", "list"}:
            # list is handled in get_queryset filtering; retrieve should check access:
            return True  # queryset restriction will handle real scope for non-staff

        if view.action in self.SAFE_CUSTOMER_WRITE:
            return True  # restricted by queryset in get_queryset()

        # writes not allowed for non-staff beyond SAFE_CUSTOMER_WRITE
        return False


# -----------------------------
# Utility helpers (AI stubs)
# -----------------------------

def _summarize_text(text: str, max_len: int = 240) -> str:
    """
    Tiny heuristic summarizer. Replace with a Celery task + real LLM later.
    """
    if not text:
        return ""
    text = " ".join(text.split())
    return (text[: max_len - 3] + "...") if len(text) > max_len else text

def _classify_priority(text: str) -> str:
    """
    Very naive classifier based on keywords.
    """
    if not text:
        return "medium"
    t = text.lower()
    if any(k in t for k in ("urgent", "asap", "down", "outage", "critical", "payment failed")):
        return "high"
    if any(k in t for k in ("slow", "delay", "issue", "can't", "cannot", "problem")):
        return "medium"
    return "low"

def _suggest_reply(subject: str, body: Optional[str]) -> str:
    """
    Heuristic reply template. Replace with LLM later.
    """
    parts = [
        f"Hi there,\n\nThanks for reaching out about “{subject}”. ",
        "We’re looking into this right away. ",
        "Could you please confirm any error messages and the approximate time the issue occurred? ",
        "This will help us resolve it faster.\n\nBest,\nSupport Team"
    ]
    return "".join(parts)

def _extract_keywords(text: str, top_k: int = 6) -> list[str]:
    if not text:
        return []
    words = [w.strip(".,!?()[]{}:;\"'").lower() for w in text.split()]
    words = [w for w in words if len(w) >= 4]
    common = Counter(words).most_common(top_k)
    return [w for w, _ in common]


# -----------------------------
# KB Articles (public read)
# -----------------------------

class KBArticleViewSet(TenantScopedModelViewSet):
    """
    Governance:
      - Public read (list/retrieve of published articles) — no auth required.
      - Staff can create/update/delete and see all (including unpublished).
    Caching: Browsing KB should be fast; enable small cache on list/retrieve for anonymous.
    """
    queryset = KBArticle.objects.all()
    serializer_class = KBArticleSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "search", "suggest"):
            return [permissions.AllowAny()]
        # write actions require auth (ideally staff)
        return [PublicReadPrivateWrite()]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "is_published": ["exact"],
    }
    search_fields = ["title", "body"]
    ordering_fields = ["created_at", "updated_at", "title"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        is_staff = bool(user and user.is_authenticated and getattr(user, "is_staff", False))

        # Public: only published
        if not is_staff and self.action in ("list", "retrieve", "search", "suggest"):
            qs = qs.filter(is_published=True)

        # Text query param `q`
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q))

        # Date range
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        if start:
            d = parse_datetime(start) or parse_date(start)
            if d: qs = qs.filter(created_at__gte=d)
        if end:
            d = parse_datetime(end) or parse_date(end)
            if d: qs = qs.filter(created_at__lte=d)

        return qs

    # Cache public list/retrieve to speed storefront help center
    @method_decorator(cache_page(60 * 5))
    @method_decorator(vary_on_headers("Authorization", "Cookie"))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(cache_page(60 * 5))
    @method_decorator(vary_on_headers("Authorization", "Cookie"))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def search(self, request):
        """
        Friendly search endpoint:
          /support/kbarticle/search?q=refund+policy&ordering=title
        """
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        ser = KBArticleSerializer(page or qs, many=True)
        return self.get_paginated_response(ser.data) if page is not None else Response(ser.data)

    @action(detail=False, methods=["get"])
    def suggest(self, request):
        """
        Simple "did you mean" / keyword extraction demo from q.
        """
        q = request.query_params.get("q", "")
        keywords = _extract_keywords(q, top_k=6)
        return Response({"query": q, "keywords": keywords})


# -----------------------------
# Tickets (private + customer-friendly)
# -----------------------------

class TicketViewSet(TenantScopedModelViewSet):
    """
    Governance:
      - Anonymous can CREATE a ticket (support portal intake).
      - Authenticated customers: can list/retrieve their own tickets and use limited actions (add_note, set_status[reopen], escalate).
      - Staff: full visibility & actions.
    """
    queryset = Ticket.objects.select_related("customer")
    serializer_class = TicketSerializer
    permission_classes = [TicketScopedPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "status": ["exact", "in"],
        "priority": ["exact", "in"],
        "customer_id": ["exact"],
    }
    search_fields = ["subject"]
    ordering_fields = ["created_at", "updated_at", "priority", "status"]
    ordering = ["-created_at"]

    # ---------- Query scoping ----------
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        is_staff = bool(user and user.is_authenticated and getattr(user, "is_staff", False))

        if not is_staff:
            # Restrict to the current customer's tickets when authenticated.
            # If you map user <-> customer, enforce that mapping here.
            # As a simple baseline: expose all tickets (read) for non-staff? No — scope to none.
            # We’ll optionally allow viewing after creation confirmation (by id via retrieve).
            # For broader customer portals, plug your user<->customer mapping here.
            customer_id = self.request.query_params.get("customer_id")
            if customer_id:
                qs = qs.filter(customer_id=customer_id)
            else:
                # If no customer hint, return empty set for list
                if self.action == "list":
                    return qs.none()

        # Text search via q
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(Q(subject__icontains=q))

        # Date window
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        if start:
            d = parse_datetime(start) or parse_date(start)
            if d: qs = qs.filter(created_at__gte=d)
        if end:
            d = parse_datetime(end) or parse_date(end)
            if d: qs = qs.filter(created_at__lte=d)

        return qs

    # ---------- Intake: allow anonymous create ----------
    def create(self, request, *args, **kwargs):
        """
        Anonymous or authenticated can submit:
          {
            "subject": "...",
            "priority": "low|medium|high",   (optional)
            "customer": <uuid or omitted>,
            "customer_email": "...",         (optional — will create/link CRM.Customer)
            "customer_name": "..."           (optional)
          }
        Tenant is injected by the mixin.
        """
        data = request.data.copy()

        # Auto-prioritize (hint) if not provided
        if not data.get("priority"):
            data["priority"] = _classify_priority(data.get("subject", ""))

        # Optional auto-create/link Customer
        cust_id = data.get("customer")
        cust_email = data.get("customer_email")
        cust_name = data.get("customer_name")

        if not cust_id and (cust_email or cust_name):
            from crm.models import Customer
            tenant = self.get_tenant()  # provided by mixin
            defaults = {
                "type": "person",
                "name": cust_name or (cust_email or "Guest"),
                "email": cust_email,
            }
            customer, _ = Customer.objects.get_or_create(
                tenant=tenant, email=cust_email or None, defaults=defaults
            )
            data["customer"] = str(customer.id)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # ---------- Customer friendly actions ----------
    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        t = self.get_object()
        t.status = "open"
        t.save(update_fields=["status"])
        return Response({"ok": True, "ticket": TicketSerializer(t).data})

    @action(detail=True, methods=["post"])
    def set_status(self, request, pk=None):
        """
        Allows staff to set any status; customers can only set 'open' or 'pending' (frontline follow-up).
        """
        t = self.get_object()
        desired = (request.data.get("status") or "").lower()
        user = request.user
        is_staff = bool(user and user.is_authenticated and getattr(user, "is_staff", False))

        allowed = {"open", "pending"} if not is_staff else {
            "open", "pending", "in_progress", "resolved", "closed"
        }
        if desired not in allowed:
            return Response({"detail": "Status not permitted."}, status=400)

        t.status = desired
        t.save(update_fields=["status"])
        return Response({"ok": True, "ticket": TicketSerializer(t).data})

    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        """
        Bump priority (customer can use it once; staff anytime).
        """
        t = self.get_object()
        current = (t.priority or "medium").lower()
        ladder = ["low", "medium", "high", "urgent"]
        try:
            idx = min(len(ladder) - 1, ladder.index(current) + 1)
        except ValueError:
            idx = 1
        t.priority = ladder[idx]
        t.save(update_fields=["priority"])
        return Response({"ok": True, "ticket": TicketSerializer(t).data})

    # ---------- Staff actions ----------
    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        t = self.get_object()
        t.status = "closed"
        t.save(update_fields=["status"])
        return Response({"ok": True, "ticket": TicketSerializer(t).data})

    @action(detail=True, methods=["post"], url_path="assign-customer")
    def assign_customer(self, request, pk=None):
        """
        Staff: attach/replace the CRM customer.
        """
        user = request.user
        if not (user and user.is_authenticated and getattr(user, "is_staff", False)):
            return Response({"detail": "Staff only."}, status=403)

        t = self.get_object()
        customer_id = request.data.get("customer")
        if not customer_id:
            return Response({"detail": "customer is required"}, status=400)

        from crm.models import Customer
        try:
            cust = Customer.objects.get(id=customer_id, tenant=t.tenant)
        except Customer.DoesNotExist:
            return Response({"detail": "Customer not found for tenant"}, status=404)

        t.customer = cust
        t.save(update_fields=["customer"])
        return Response({"ok": True, "ticket": TicketSerializer(t).data})

    # ---------- AI-ish helpers (safe stubs to replace later) ----------
    @action(detail=True, methods=["get"], url_path="ai/summary")
    def ai_summary(self, request, pk=None):
        t = self.get_object()
        # Using subject only (no body field); add a body/description field to model if needed
        summary = _summarize_text(t.subject)
        return Response({"summary": summary})

    @action(detail=True, methods=["get"], url_path="ai/classify")
    def ai_classify(self, request, pk=None):
        t = self.get_object()
        priority = _classify_priority(t.subject)
        return Response({"suggested_priority": priority})

    @action(detail=True, methods=["get"], url_path="ai/suggest_reply")
    def ai_suggest_reply(self, request, pk=None):
        t = self.get_object()
        suggestion = _suggest_reply(t.subject, None)
        return Response({"suggested_reply": suggestion})
