from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    DepartmentViewSet, PositionViewSet, EmployeeViewSet, ShiftViewSet,
    PaystubViewSet,
    AttendanceViewSet, LeaveRequestViewSet,
    BenefitViewSet, EmployeeBenefitViewSet,
    PayRunViewSet, PaystubViewSet,
    HRDocumentViewSet, OnboardingTaskViewSet
)

router = DefaultRouter()
router.register(r'department', DepartmentViewSet, basename='hr-department')
router.register(r'position', PositionViewSet, basename='hr-position')
router.register(r'employee', EmployeeViewSet, basename='hr-employee')
router.register(r'shift', ShiftViewSet, basename='hr-shift')
router.register(r'attendance', AttendanceViewSet, basename='hr-attendance')
router.register(r'leave', LeaveRequestViewSet, basename='hr-leave')
router.register(r'benefit', BenefitViewSet, basename='hr-benefit')
router.register(r'employee-benefit', EmployeeBenefitViewSet, basename='hr-employee-benefit')
router.register(r'payrun', PayRunViewSet, basename='hr-payrun')
router.register(r'paystub', PaystubViewSet, basename='hr-paystub')

router.register(r'document', HRDocumentViewSet, basename='hr-document')
router.register(r'onboarding', OnboardingTaskViewSet, basename='hr-onboarding')

urlpatterns = [path('', include(router.urls))]
