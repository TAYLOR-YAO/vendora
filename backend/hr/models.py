from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from common.models import BaseModel


class Department(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="hr_departments")
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE, related_name="hr_departments")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=24, blank=True, null=True)

    class Meta:
        unique_together = (("tenant", "business", "name"),)
        indexes = [models.Index(fields=["tenant", "business", "name"])]

    def __str__(self) -> str:
        return self.name


class Position(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="hr_positions")
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE, related_name="hr_positions")
    title = models.CharField(max_length=160)
    department = models.ForeignKey("hr.Department", on_delete=models.SET_NULL, null=True, blank=True, related_name="positions")
    grade = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=["tenant", "business", "title"])]

    def __str__(self) -> str:
        return self.title


class Employee(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="employees")
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE, related_name="employees")
    store = models.ForeignKey("business.Store", on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey("hr.Department", on_delete=models.SET_NULL, null=True, blank=True)
    position = models.ForeignKey("hr.Position", on_delete=models.SET_NULL, null=True, blank=True)

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        ON_LEAVE = 'on_leave', _('On Leave')
        TERMINATED = 'terminated', _('Terminated')

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    hire_date = models.DateField(blank=True, null=True)
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    meta_json = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=["tenant", "business", "status", "last_name", "first_name"])]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name or ''}".strip()


class Shift(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="hr_shifts")
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE, related_name="hr_shifts")
    store = models.ForeignKey("business.Store", on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100, default="Default")
    start_time = models.TimeField()
    end_time = models.TimeField()
    timezone = models.CharField(max_length=64, default="UTC")


class Attendance(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="hr_attendance")
    employee = models.ForeignKey("hr.Employee", on_delete=models.CASCADE, related_name="attendance")
    clock_in_at = models.DateTimeField()
    clock_out_at = models.DateTimeField(null=True, blank=True)
    method = models.CharField(max_length=20, default="manual")  # manual|geo|kiosk|api
    geo_lat = models.FloatField(null=True, blank=True)
    geo_lng = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=["tenant", "employee", "clock_in_at"])]


class LeaveRequest(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="hr_leaves")
    employee = models.ForeignKey("hr.Employee", on_delete=models.CASCADE, related_name="leaves")
    leave_type = models.CharField(max_length=32, default="annual")
    start_date = models.DateField()
    end_date = models.DateField()

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        APPROVED = 'approved', _('Approved')
        REJECTED = 'rejected', _('Rejected')
        CANCELLED = 'cancelled', _('Cancelled')

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    reason = models.TextField(blank=True, null=True)
    approver_user_id = models.UUIDField(null=True, blank=True)


class Benefit(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="hr_benefits")
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE, related_name="hr_benefits")
    name = models.CharField(max_length=120)
    config = models.JSONField(default=dict, blank=True)


class EmployeeBenefit(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="hr_employee_benefits")
    employee = models.ForeignKey("hr.Employee", on_delete=models.CASCADE, related_name="employee_benefits")
    benefit = models.ForeignKey("hr.Benefit", on_delete=models.CASCADE, related_name="enrollments")
    effective_date = models.DateField(default=timezone.now)

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        ENDED = 'ended', _('Ended')

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)


class PayRun(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="hr_payruns")
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE, related_name="hr_payruns")
    period_start = models.DateField()
    period_end = models.DateField()

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        PROCESSING = 'processing', _('Processing')
        FINALIZED = 'finalized', _('Finalized')

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    meta_json = models.JSONField(default=dict, blank=True)


class Paystub(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="hr_payslips")
    employee = models.ForeignKey("hr.Employee", on_delete=models.CASCADE, related_name="payslips")
    payrun = models.ForeignKey("hr.PayRun", on_delete=models.CASCADE, related_name="payslips")
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="XOF")
    pdf_url = models.URLField(blank=True, null=True)

# class Payslip(BaseModel):
#     tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="hr_payslips")
#     employee = models.ForeignKey("hr.Employee", on_delete=models.CASCADE, related_name="payslips")
#     payrun = models.ForeignKey("hr.PayRun", on_delete=models.CASCADE, related_name="payslips")
#     gross_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
#     net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
#     currency = models.CharField(max_length=3, default="XOF")
#     pdf_url = models.URLField(blank=True, null=True)

class HRDocument(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="hr_documents")
    employee = models.ForeignKey("hr.Employee", on_delete=models.CASCADE, related_name="documents")
    kind = models.CharField(max_length=32, default="id")  # id|contract|certificate|custom
    title = models.CharField(max_length=160)
    url = models.URLField()
    issued_at = models.DateField(null=True, blank=True)


class OnboardingTask(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="hr_onboarding_tasks")
    employee = models.ForeignKey("hr.Employee", on_delete=models.CASCADE, related_name="onboarding_tasks")
    title = models.CharField(max_length=160)
    due_date = models.DateField(null=True, blank=True)

    class Status(models.TextChoices):
        OPEN = 'open', _('Open')
        DONE = 'done', _('Done')
        SKIPPED = 'skipped', _('Skipped')

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
