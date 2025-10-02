from rest_framework import viewsets
from .models import Employee
from .serializers import EmployeeSerializer

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all().order_by('-id') if hasattr(Employee, 'id') else Employee.objects.all()
    serializer_class = EmployeeSerializer
