from datetime import datetime
from django.db.models import Q, F
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from rest_framework import status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend

from common.mixins import TenantScopedModelViewSet
from platformapp.permissions import IsTenantOperatorOrAdmin  # you added this earlier
from .models import (
    Department, Position, Employee, Shift, Attendance, LeaveRequest,
    Benefit, EmployeeBenefit, PayRun, Paystub, HRDocument, OnboardingTask
)
from .serializers import (
    DepartmentSerializer, PositionSerializer, EmployeeSerializer, ShiftSerializer,
    AttendanceSerializer, LeaveRequestSerializer, BenefitSerializer, EmployeeBenefitSerializer,
    PayRunSerializer, PaystubSerializer, HRDocumentSerializer, OnboardingTaskSerializer
)


# --------- Base helpers ---------
READ_FILTERS = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


def _apply_common_filters(view, request, qs, search_fields):
    """Apply 'q' keyword search in addition to SearchFilter so both work."""
    q = request.query_params.get("q")
    if q:
        # OR across fields
        search = Q()
        for f in search_fields:
            search |= Q(**{f"{f}__icontains": q})
        qs = qs.filter(search)
    return qs


# --------- Department / Position ---------
class DepartmentViewSet(TenantScopedModelViewSet):
    queryset = Department.objects.select_related("business")
    serializer_class = DepartmentSerializer
    permission_classes = [IsTenantOperatorOrAdmin | permissions.IsAuthenticated]
    filter_backends = READ_FILTERS
    search_fields = ["name", "code"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        return _apply_common_filters(self, self.request, qs, self.search_fields)


class PositionViewSet(TenantScopedModelViewSet):
    queryset = Position.objects.select_related("business", "department")
    serializer_class = PositionSerializer
    permission_classes = [IsTenantOperatorOrAdmin | permissions.IsAuthenticated]
    filter_backends = READ_FILTERS
    search_fields = ["title", "grade", "department__name"]
    ordering_fields = ["title", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        return _apply_common_filters(self, self.request, qs, self.search_fields)


# --------- Employee ---------
class EmployeeViewSet(TenantScopedModelViewSet):
    queryset = (
        Employee.objects
        .select_related("business", "store", "department", "position")
        .order_by("-created_at")
    )
    serializer_class = EmployeeSerializer
    permission_classes = [IsTenantOperatorOrAdmin | permissions.IsAuthenticated]
    filter_backends = READ_FILTERS
    search_fields = ["first_name", "last_name", "email", "phone", "department__name", "position__title"]
    ordering_fields = ["first_name", "last_name", "hire_date", "created_at", "status"]
    filterset_fields = ["status", "store", "department", "position", "business"]

    def get_queryset(self):
        qs = super().get_queryset()
        return _apply_common_filters(self, self.request, qs, self.search_fields)

    @action(detail=True, methods=["post"], permission_classes=[IsTenantOperatorOrAdmin])
    def terminate(self, request, pk=None):
        emp = self.get_object()
        emp.status = Employee.Status.TERMINATED
        emp.save(update_fields=["status"])
        return Response({"ok": True})

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def summary(self, request, pk=None):
        emp = self.get_object()
        payload = {
            "id": str(emp.id),
            "full_name": f"{emp.first_name} {emp.last_name or ''}".strip(),
            "status": emp.status,
            "hire_date": emp.hire_date,
            "open_tasks": emp.onboarding_tasks.filter(status="open").count(),
            "pending_leaves": emp.leaves.filter(status="pending").count(),
        }
        return Response(payload)

    # AI hook: lightweight suggestion endpoint
    @action(detail=True, methods=["get"], url_path="ai/suggest", permission_classes=[IsTenantOperatorOrAdmin])
    def ai_suggest(self, request, pk=None):
        emp = self.get_object()
        # TODO: call aiapp (e.g., HTTP/gRPC) with employee stats to get coaching tips
        suggestion = {
            "coaching_tip": _("Consider assigning {employee_name} a mentor in {department_name} to speed up onboarding.").format(employee_name=emp.first_name, department_name=emp.department.name if emp.department else _("their department")),
            "confidence": 0.62,
        }
        return Response(suggestion)


# --------- Attendance ---------
class AttendanceViewSet(TenantScopedModelViewSet):
    queryset = Attendance.objects.select_related("employee").order_by("-clock_in_at")
    serializer_class = AttendanceSerializer
    permission_classes = [IsTenantOperatorOrAdmin | permissions.IsAuthenticated]
    filter_backends = READ_FILTERS
    search_fields = ["employee__first_name", "employee__last_name", "notes", "method"]
    ordering_fields = ["clock_in_at", "clock_out_at", "created_at"]
    filterset_fields = ["employee", "method"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = _apply_common_filters(self, self.request, qs, self.search_fields)
        # Optional: date range filter
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        if start:
            qs = qs.filter(clock_in_at__date__gte=start)
        if end:
            qs = qs.filter(clock_in_at__date__lte=end)
        return qs

    @action(detail=False, methods=["post"], url_path="clock-in", permission_classes=[permissions.IsAuthenticated])
    def clock_in(self, request):
        employee_id = request.data.get("employee_id")
        lat = request.data.get("geo_lat")
        lng = request.data.get("geo_lng")
        now = timezone.now()
        att = Attendance.objects.create(
            tenant=self.get_tenant(request),
            employee_id=employee_id,
            clock_in_at=now,
            method="api",
            geo_lat=lat,
            geo_lng=lng,
        )
        return Response({"ok": True, "attendance_id": str(att.id), "clock_in_at": now})

    @action(detail=True, methods=["post"], url_path="clock-out", permission_classes=[permissions.IsAuthenticated])
    def clock_out(self, request, pk=None):
        att = self.get_object()
        if att.clock_out_at:
            return Response({"detail": _("Already clocked out.")}, status=status.HTTP_400_BAD_REQUEST)
        att.clock_out_at = timezone.now()
        att.save(update_fields=["clock_out_at"])
        return Response({"ok": True, "clock_out_at": att.clock_out_at})

    @action(detail=False, methods=["get"], url_path="summary", permission_classes=[IsTenantOperatorOrAdmin])
    def summary(self, request):
        # Simple summary; can be replaced with analyticsapp aggregation
        qs = self.filter_queryset(self.get_queryset())
        total = qs.count()
        open_sessions = qs.filter(clock_out_at__isnull=True).count()
        return Response({"total": total, "open_sessions": open_sessions})


# --------- Leave ---------
class LeaveRequestViewSet(TenantScopedModelViewSet):
    queryset = LeaveRequest.objects.select_related("employee").order_by("-created_at")
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsTenantOperatorOrAdmin | permissions.IsAuthenticated]
    filter_backends = READ_FILTERS
    search_fields = ["employee__first_name", "employee__last_name", "reason", "leave_type", "status"]
    ordering_fields = ["start_date", "end_date", "created_at", "status"]
    filterset_fields = ["employee", "leave_type", "status"]

    def get_queryset(self):
        qs = super().get_queryset()
        return _apply_common_filters(self, self.request, qs, self.search_fields)

    @action(detail=True, methods=["post"], url_path="approve", permission_classes=[IsTenantOperatorOrAdmin])
    def approve(self, request, pk=None):
        obj = self.get_object()
        obj.status = LeaveRequest.Status.APPROVED
        obj.approver_user_id = request.user.id if request.user and request.user.is_authenticated else None
        obj.save(update_fields=["status", "approver_user_id"])
        return Response({"ok": True})

    @action(detail=True, methods=["post"], url_path="reject", permission_classes=[IsTenantOperatorOrAdmin])
    def reject(self, request, pk=None):
        obj = self.get_object()
        obj.status = LeaveRequest.Status.REJECTED
        obj.approver_user_id = request.user.id if request.user and request.user.is_authenticated else None
        obj.save(update_fields=["status", "approver_user_id"])
        return Response({"ok": True})


# --------- Benefits ---------
class BenefitViewSet(TenantScopedModelViewSet):
    queryset = Benefit.objects.select_related("business")
    serializer_class = BenefitSerializer
    permission_classes = [IsTenantOperatorOrAdmin | permissions.IsAuthenticated]
    filter_backends = READ_FILTERS
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        return _apply_common_filters(self, self.request, qs, self.search_fields)


class EmployeeBenefitViewSet(TenantScopedModelViewSet):
    queryset = EmployeeBenefit.objects.select_related("employee", "benefit")
    serializer_class = EmployeeBenefitSerializer
    permission_classes = [IsTenantOperatorOrAdmin | permissions.IsAuthenticated]
    filter_backends = READ_FILTERS
    search_fields = ["employee__first_name", "employee__last_name", "benefit__name", "status"]
    ordering_fields = ["effective_date", "created_at", "status"]
    filterset_fields = ["employee", "benefit", "status"]

    def get_queryset(self):
        qs = super().get_queryset()
        return _apply_common_filters(self, self.request, qs, self.search_fields)


# --------- Payroll ---------
class PayRunViewSet(TenantScopedModelViewSet):
    queryset = PayRun.objects.select_related("business").order_by("-period_end")
    serializer_class = PayRunSerializer
    permission_classes = [IsTenantOperatorOrAdmin | permissions.IsAuthenticated]
    filter_backends = READ_FILTERS
    search_fields = ["status"]
    ordering_fields = ["period_start", "period_end", "created_at", "status"]

    def get_queryset(self):
        qs = super().get_queryset()
        return _apply_common_filters(self, self.request, qs, self.search_fields)

    @action(detail=True, methods=["post"], url_path="finalize", permission_classes=[IsTenantOperatorOrAdmin])
    def finalize(self, request, pk=None):
        pr = self.get_object()
        pr.status = PayRun.Status.FINALIZED
        pr.save(update_fields=["status"])
        return Response({"ok": True})


# --------- Documents & Onboarding ---------
class HRDocumentViewSet(TenantScopedModelViewSet):
    queryset = HRDocument.objects.select_related("employee").order_by("-created_at")
    serializer_class = HRDocumentSerializer
    permission_classes = [IsTenantOperatorOrAdmin | permissions.IsAuthenticated]
    filter_backends = READ_FILTERS
    search_fields = ["title", "kind", "employee__first_name", "employee__last_name"]
    ordering_fields = ["issued_at", "created_at"]
    filterset_fields = ["employee", "kind"]

    def get_queryset(self):
        qs = super().get_queryset()
        return _apply_common_filters(self, self.request, qs, self.search_fields)


class OnboardingTaskViewSet(TenantScopedModelViewSet):
    queryset = OnboardingTask.objects.select_related("employee").order_by("status", "due_date")
    serializer_class = OnboardingTaskSerializer
    permission_classes = [IsTenantOperatorOrAdmin | permissions.IsAuthenticated]
    filter_backends = READ_FILTERS
    search_fields = ["title", "employee__first_name", "employee__last_name", "status"]
    ordering_fields = ["due_date", "created_at", "status"]
    filterset_fields = ["employee", "status"]

    def get_queryset(self):
        qs = super().get_queryset()
        return _apply_common_filters(self, self.request, qs, self.search_fields)

    @action(detail=True, methods=["post"], url_path="done", permission_classes=[permissions.IsAuthenticated])
    def mark_done(self, request, pk=None):
        task = self.get_object()
        task.status = OnboardingTask.Status.DONE
        task.save(update_fields=["status"])
        return Response({"ok": True})


class ShiftViewSet(TenantScopedModelViewSet):
    """
    Manage scheduled work shifts for employees.
    Useful for attendance, payroll, and location-based validation.
    """
    queryset = Shift.objects.select_related("employee", "business", "store").order_by("-start_time")
    serializer_class = ShiftSerializer
    permission_classes = [IsTenantOperatorOrAdmin]
    filterset_fields = {
        "employee": ["exact"],
        "business": ["exact"],
        "store": ["exact"],
        "status": ["exact"],
    }
    search_fields = ["employee__first_name", "employee__last_name"]

    @action(detail=True, methods=["post"], url_path="start")
    def start_shift(self, request, pk=None):
        shift = self.get_object()
        shift.status = "in_progress"
        shift.save(update_fields=["status"])
        return Response({"ok": True, "status": shift.status}, status=200)

    @action(detail=True, methods=["post"], url_path="end")
    def end_shift(self, request, pk=None):
        shift = self.get_object()
        shift.status = "completed"
        shift.save(update_fields=["status"])
        return Response({"ok": True, "status": shift.status}, status=200)

# -------------------------------------------------------------------------
# ATTENDANCE MANAGEMENT
# -------------------------------------------------------------------------
class AttendanceViewSet(TenantScopedModelViewSet):
    """
    Log employee attendance for compliance and payroll.
    Includes location verification (if coordinates are provided).
    """
    queryset = Attendance.objects.select_related("employee", "business", "store").order_by("-created_at")
    serializer_class = AttendanceSerializer
    permission_classes = [IsTenantOperatorOrAdmin]
    filterset_fields = {
        "employee": ["exact"],
        "business": ["exact"],
        "store": ["exact"],
        "status": ["exact"],
    }
    search_fields = ["employee__first_name", "employee__last_name"]

    @action(detail=True, methods=["post"], url_path="verify")
    def verify_location(self, request, pk=None):
        att = self.get_object()
        # Example: location verification placeholder
        if att.latitude and att.longitude:
            verified = True
        else:
            verified = False
        return Response({"verified": verified}, status=200)


# -------------------------------------------------------------------------
# PAYROLL MANAGEMENT
# -------------------------------------------------------------------------
class PaystubViewSet(TenantScopedModelViewSet):
    """
    Manage employee paystubs and payroll records.
    Integrates with shifts and attendance to calculate payable hours.
    """
    queryset = Paystub.objects.select_related("employee", "business").order_by("-created_at")
    serializer_class = PaystubSerializer
    permission_classes = [IsTenantOperatorOrAdmin]
    filterset_fields = {
        "employee": ["exact"],
        "business": ["exact"],
        "status": ["exact"],
    }
    search_fields = ["employee__first_name", "employee__last_name", "reference"]

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        paystub = self.get_object()
        paystub.status = "paid"
        paystub.save(update_fields=["status"])
        return Response({"ok": True, "status": paystub.status}, status=200)