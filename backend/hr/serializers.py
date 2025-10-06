from rest_framework import serializers
from .models import (
    Department, Position, Employee, Shift, Attendance, LeaveRequest,
    Benefit, EmployeeBenefit, PayRun,
    Paystub, 
    HRDocument, OnboardingTask
)


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"
        read_only_fields = ("tenant", "business", "created_at", "updated_at")


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = "__all__"
        read_only_fields = ("tenant", "business", "created_at", "updated_at")


class EmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = "__all__"
        read_only_fields = ("tenant", "business", "created_at", "updated_at")

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name or ''}".strip()


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = "__all__"
        read_only_fields = ("tenant", "business", "created_at", "updated_at")


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at")


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = ("tenant", "status", "created_at", "updated_at")


class BenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Benefit
        fields = "__all__"
        read_only_fields = ("tenant", "business", "created_at", "updated_at")


class EmployeeBenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeBenefit
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at")


class PayRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayRun
        fields = "__all__"
        read_only_fields = ("tenant", "business", "created_at", "updated_at")



class PaystubSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.__str__", read_only=True)

    class Meta:
        model = Paystub
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at")

class HRDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRDocument
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at")


class OnboardingTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingTask
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at")
