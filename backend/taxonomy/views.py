from typing import Optional, Dict, Any, List
from collections import Counter

from django.db.models import Q, Prefetch
from django.utils.dateparse import parse_datetime, parse_date
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from common.mixins import TenantScopedModelViewSet
from platformapp.models import Tenant
from .models import Industry, Category, Subcategory
from .serializers import IndustrySerializer, CategorySerializer, SubcategorySerializer


# -----------------------------
# Permissions aligned to policy
# -----------------------------

class PublicReadPrivateWrite(permissions.BasePermission):
    """
    - Allow anyone to read (list/retrieve and public helper endpoints).
    - Require auth for write actions.
    """
    PUBLIC_ACTIONS = {"list", "retrieve", "tree", "breadcrumbs", "suggest"}

    def has_permission(self, request, view):
        if view.action in self.PUBLIC_ACTIONS:
            return True
        return bool(request.user and request.user.is_authenticated)


# -----------------------------
# Small keyword helper (AI stub)
# -----------------------------

def _extract_keywords(text: str, top_k: int = 6) -> list[str]:
    if not text:
        return []
    words = [w.strip(".,!?()[]{}:;\"'").lower() for w in text.split()]
    words = [w for w in words if len(w) >= 3]
    common = Counter(words).most_common(top_k)
    return [w for w, _ in common]


# -----------------------------
# Tenant resolution fallback
# -----------------------------

def _resolve_tenant_from_request(request) -> Optional[Tenant]:
    """
    Your TenantScopedModelViewSet likely already resolves tenant
    (header X-Tenant-Id/X-Tenant-Slug, query tenant/tenant_slug, etc.)
    This helper is a fallback for public endpoints.
    """
    tid = request.headers.get("X-Tenant-Id") or request.query_params.get("tenant_id") or request.query_params.get("tenant")
    slug = request.headers.get("X-Tenant-Slug") or request.query_params.get("tenant_slug")
    if tid:
        try:
            return Tenant.objects.get(id=tid)
        except Tenant.DoesNotExist:
            return None
    if slug:
        try:
            return Tenant.objects.get(slug=slug)
        except Tenant.DoesNotExist:
            return None
    return None


# -----------------------------
# Industry
# -----------------------------

class IndustryViewSet(TenantScopedModelViewSet):
    """
    Governance:
      - Public browse/search (no auth).
      - Staff (or permitted roles) can CRUD.
    Filtering:
      - q (search name/slug)
      - slug exact
      - created_at range: start, end
    Ordering:
      - created_at, updated_at, name, slug
    """
    queryset = Industry.objects.all()
    serializer_class = IndustrySerializer
    permission_classes = [PublicReadPrivateWrite]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {"slug": ["exact", "in"]}
    search_fields = ["name", "slug"]
    ordering_fields = ["created_at", "updated_at", "name", "slug"]
    ordering = ["name"]

    def get_queryset(self):
        qs = super().get_queryset()

        # Optional broad search
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(slug__icontains=q))

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

    # Cache public list/retrieve (still vary by auth for staff vs public differences)
    @method_decorator(cache_page(60 * 10))
    @method_decorator(vary_on_headers("Authorization", "Cookie", "X-Tenant-Id", "X-Tenant-Slug"))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(cache_page(60 * 10))
    @method_decorator(vary_on_headers("Authorization", "Cookie", "X-Tenant-Id", "X-Tenant-Slug"))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def suggest(self, request):
        """
        Keyword helper for typeaheads: /taxonomy/industry/suggest?q=foo
        """
        q = request.query_params.get("q", "")
        tokens = _extract_keywords(q, 6)
        return Response({"query": q, "keywords": tokens})

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def bulk_upsert(self, request):
        """
        Staff utility: [{id?, slug, name}]
        """
        user = request.user
        if not getattr(user, "is_staff", False):
            return Response({"detail": "Staff only."}, status=403)

        payload = request.data
        if not isinstance(payload, list):
            return Response({"detail": "Expected a list."}, status=400)

        created_or_updated = []
        tenant = self.get_tenant() or _resolve_tenant_from_request(request)
        if not tenant:
            return Response({"detail": "Tenant not resolved."}, status=400)

        for item in payload:
            iid = item.get("id")
            defaults = {"name": item.get("name"), "slug": item.get("slug"), "tenant": tenant}
            if iid:
                try:
                    obj = Industry.objects.get(id=iid, tenant=tenant)
                    for k in ("name", "slug"):
                        if k in item and item[k] is not None:
                            setattr(obj, k, item[k])
                    obj.save()
                except Industry.DoesNotExist:
                    obj = Industry.objects.create(**defaults)
            else:
                obj = Industry.objects.create(**defaults)
            created_or_updated.append(IndustrySerializer(obj).data)

        return Response({"items": created_or_updated})


# -----------------------------
# Category
# -----------------------------

class CategoryViewSet(TenantScopedModelViewSet):
    queryset = Category.objects.select_related("industry")
    serializer_class = CategorySerializer
    permission_classes = [PublicReadPrivateWrite]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "slug": ["exact", "in"],
        "industry_id": ["exact"],
    }
    search_fields = ["name", "slug", "industry__name", "industry__slug"]
    ordering_fields = ["created_at", "updated_at", "name", "slug"]
    ordering = ["name"]

    def get_queryset(self):
        qs = super().get_queryset()

        # Optional free text search
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(slug__icontains=q) |
                Q(industry__name__icontains=q) |
                Q(industry__slug__icontains=q)
            )

        # Industry scoping via industry_slug
        ind_slug = self.request.query_params.get("industry_slug")
        if ind_slug:
            qs = qs.filter(industry__slug=ind_slug)

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

    @method_decorator(cache_page(60 * 10))
    @method_decorator(vary_on_headers("Authorization", "Cookie", "X-Tenant-Id", "X-Tenant-Slug"))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(cache_page(60 * 10))
    @method_decorator(vary_on_headers("Authorization", "Cookie", "X-Tenant-Id", "X-Tenant-Slug"))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def suggest(self, request):
        q = request.query_params.get("q", "")
        tokens = _extract_keywords(q, 6)
        return Response({"query": q, "keywords": tokens})


# -----------------------------
# Subcategory
# -----------------------------

class SubcategoryViewSet(TenantScopedModelViewSet):
    queryset = Subcategory.objects.select_related("category", "category__industry")
    serializer_class = SubcategorySerializer
    permission_classes = [PublicReadPrivateWrite]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "slug": ["exact", "in"],
        "category_id": ["exact"],
    }
    search_fields = [
        "name", "slug",
        "category__name", "category__slug",
        "category__industry__name", "category__industry__slug"
    ]
    ordering_fields = ["created_at", "updated_at", "name", "slug"]
    ordering = ["name"]

    def get_queryset(self):
        qs = super().get_queryset()

        # Optional search
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(slug__icontains=q) |
                Q(category__name__icontains=q) |
                Q(category__slug__icontains=q) |
                Q(category__industry__name__icontains=q) |
                Q(category__industry__slug__icontains=q)
            )

        # Category scoping via category_slug
        cat_slug = self.request.query_params.get("category_slug")
        if cat_slug:
            qs = qs.filter(category__slug=cat_slug)

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

    @method_decorator(cache_page(60 * 10))
    @method_decorator(vary_on_headers("Authorization", "Cookie", "X-Tenant-Id", "X-Tenant-Slug"))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(cache_page(60 * 10))
    @method_decorator(vary_on_headers("Authorization", "Cookie", "X-Tenant-Id", "X-Tenant-Slug"))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def suggest(self, request):
        q = request.query_params.get("q", "")
        tokens = _extract_keywords(q, 6)
        return Response({"query": q, "keywords": tokens})


# -----------------------------
# Cross-entity helpers
# -----------------------------

class TaxonomyTreeMixin:
    """
    Provides a shared /tree endpoint building:
    Industry -> categories -> subcategories
    """
    @staticmethod
    def build_tree(tenant: Tenant) -> List[Dict[str, Any]]:
        industries = (
            Industry.objects
            .filter(tenant=tenant)
            .order_by("name")
            .prefetch_related(
                Prefetch(
                    "categories",
                    queryset=Category.objects.filter(tenant=tenant).order_by("name").prefetch_related(
                        Prefetch("subcategories", queryset=Subcategory.objects.filter(tenant=tenant).order_by("name"))
                    )
                )
            )
        )
        out = []
        for ind in industries:
            ind_node = {"id": str(ind.id), "name": ind.name, "slug": ind.slug, "categories": []}
            for cat in ind.categories.all():
                cat_node = {"id": str(cat.id), "name": cat.name, "slug": cat.slug, "subcategories": []}
                for sub in cat.subcategories.all():
                    cat_node["subcategories"].append({"id": str(sub.id), "name": sub.name, "slug": sub.slug})
                ind_node["categories"].append(cat_node)
            out.append(ind_node)
        return out


# Attach tree & breadcrumbs to IndustryViewSet (most natural entry point)
IndustryViewSet.__doc__ = (IndustryViewSet.__doc__ or "") + "\n\nIncludes /tree and /breadcrumbs endpoints."

@action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
def tree(self, request):
    """
    Public tree:
      /taxonomy/industry/tree?tenant_slug=acme
    """
    tenant = self.get_tenant() or _resolve_tenant_from_request(request)
    if not tenant:
        return Response({"detail": "Tenant not resolved. Provide tenant or tenant_slug."}, status=400)
    data = TaxonomyTreeMixin.build_tree(tenant)
    return Response({"tenant": tenant.slug, "tree": data})

def breadcrumbs(self, request):
    """
    Build simple breadcrumbs from any of: industry_slug, category_slug, subcategory_slug
    """
    tenant = self.get_tenant() or _resolve_tenant_from_request(request)
    if not tenant:
        return Response({"detail": "Tenant not resolved."}, status=400)

    ind_slug = request.query_params.get("industry_slug")
    cat_slug = request.query_params.get("category_slug")
    sub_slug = request.query_params.get("subcategory_slug")

    trail: List[Dict[str, Any]] = []

    try:
        if sub_slug:
            sub = Subcategory.objects.get(tenant=tenant, slug=sub_slug)
            cat = sub.category
            ind = cat.industry
            trail = [
                {"type": "industry", "id": str(ind.id), "name": ind.name, "slug": ind.slug},
                {"type": "category", "id": str(cat.id), "name": cat.name, "slug": cat.slug},
                {"type": "subcategory", "id": str(sub.id), "name": sub.name, "slug": sub.slug},
            ]
        elif cat_slug:
            cat = Category.objects.get(tenant=tenant, slug=cat_slug)
            ind = cat.industry
            trail = [
                {"type": "industry", "id": str(ind.id), "name": ind.name, "slug": ind.slug},
                {"type": "category", "id": str(cat.id), "name": cat.name, "slug": cat.slug},
            ]
        elif ind_slug:
            ind = Industry.objects.get(tenant=tenant, slug=ind_slug)
            trail = [{"type": "industry", "id": str(ind.id), "name": ind.name, "slug": ind.slug}]
        else:
            return Response({"detail": "Provide industry_slug or category_slug or subcategory_slug"}, status=400)
    except (Industry.DoesNotExist, Category.DoesNotExist, Subcategory.DoesNotExist):
        return Response({"detail": "Not found for tenant."}, status=404)

    return Response({"tenant": tenant.slug, "breadcrumbs": trail})

# Bind actions to the class (so the router picks them up)
IndustryViewSet.tree = tree
IndustryViewSet.breadcrumbs = action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])(breadcrumbs)
