from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from common.mixins import TenantScopedModelViewSet
from common.permissions import PrivateTenantOnly  # auth + X-Tenant-ID required for all methods

from .models import Customer, Contact, Pipeline, Opportunity, Activity
from .serializers import (
    CustomerSerializer, CustomerListSerializer,
    ContactSerializer, PipelineSerializer,
    OpportunitySerializer, OpportunityListSerializer,
    ActivitySerializer
)


class DefaultPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


# ---------- Private ViewSets (no public browse) ----------
class CustomerViewSet(TenantScopedModelViewSet):
    permission_classes = [PrivateTenantOnly]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "status": ["exact"],
        "marketing_consent": ["exact"],
        "type": ["exact"],
    }
    search_fields = ["name","first_name","last_name","company","email","phone","tags"]
    ordering_fields = ["created_at","updated_at","name"]
    ordering = ["-created_at"]

    queryset = Customer.objects.all()

    def get_serializer_class(self):
        return CustomerListSerializer if self.action == "list" else CustomerSerializer


class ContactViewSet(TenantScopedModelViewSet):
    permission_classes = [PrivateTenantOnly]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {"customer":["exact"], "is_primary":["exact"]}
    search_fields = ["first_name","last_name","email","phone"]
    ordering_fields = ["created_at","updated_at","first_name","last_name"]
    ordering = ["-created_at"]

    queryset = Contact.objects.select_related("customer")
    serializer_class = ContactSerializer


class PipelineViewSet(TenantScopedModelViewSet):
    permission_classes = [PrivateTenantOnly]
    pagination_class = DefaultPagination
    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer


class OpportunityViewSet(TenantScopedModelViewSet):
    permission_classes = [PrivateTenantOnly]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {"stage":["exact"], "owner_user_id":["exact"], "customer":["exact"]}
    search_fields = ["name","source","tags"]
    ordering_fields = ["created_at","updated_at","amount","expected_close","probability"]
    ordering = ["-created_at"]

    queryset = Opportunity.objects.select_related("customer","pipeline")
    def get_serializer_class(self):
        return OpportunityListSerializer if self.action == "list" else OpportunitySerializer


class ActivityViewSet(TenantScopedModelViewSet):
    permission_classes = [PrivateTenantOnly]
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {"kind":["exact"], "customer":["exact"], "opportunity":["exact"]}
    search_fields = ["content"]
    ordering_fields = ["created_at","updated_at","due_at","completed_at"]
    ordering = ["-created_at"]

    queryset = Activity.objects.select_related("customer","opportunity")
    serializer_class = ActivitySerializer


# ---------- Public lead intake (optional & rate-limited) ----------
class LeadIntakeThrottle(AnonRateThrottle):
    rate = "10/hour"  # tune to your needs


class LeadIntakeAPIView(APIView):
    """
    Public endpoint to submit a lead (no auth).
    Required: tenant_slug and at least one of name/email/phone.
    It will upsert a Customer by email within the tenant, set marketing_consent if provided.
    """
    throttle_classes = [LeadIntakeThrottle]

    def post(self, request):
        tenant_slug = request.data.get("tenant_slug")
        name  = request.data.get("name")
        email = request.data.get("email")
        phone = request.data.get("phone")
        consent = bool(request.data.get("marketing_consent", False))
        source  = request.data.get("source") or "webform"
        meta    = request.data.get("meta_json") or {}

        if not tenant_slug:
            return Response({"detail": "tenant_slug is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not any([name, email, phone]):
            return Response({"detail": "Provide at least one of name/email/phone"}, status=status.HTTP_400_BAD_REQUEST)

        from platformapp.models import Tenant
        try:
            tenant = Tenant.objects.get(slug=tenant_slug, status="active")
        except Tenant.DoesNotExist:
            return Response({"detail": "Invalid tenant_slug"}, status=status.HTTP_404_NOT_FOUND)

        # upsert by email (if provided) within tenant
        if email:
            customer, created = Customer.objects.get_or_create(
                tenant=tenant, email=email,
                defaults={
                    "type": "person",
                    "name": name or email,
                    "phone": phone,
                    "marketing_consent": consent,
                    "consent_ts": timezone.now() if consent else None,
                    "source": source,
                    "meta_json": meta,
                },
            )
            if not created:
                # update minimal fields (avoid overwriting richer internal data)
                changed = False
                if name and not customer.name:
                    customer.name = name; changed = True
                if phone and not customer.phone:
                    customer.phone = phone; changed = True
                if consent and not customer.marketing_consent:
                    customer.marketing_consent = True
                    customer.consent_ts = timezone.now()
                    changed = True
                if changed:
                    customer.save()
        else:
            customer = Customer.objects.create(
                tenant=tenant, type="person", name=name or (phone or "Lead"),
                phone=phone, source=source, marketing_consent=consent,
                consent_ts=timezone.now() if consent else None, meta_json=meta
            )

        return Response({"id": str(customer.id), "created_at": customer.created_at}, status=status.HTTP_201_CREATED)
