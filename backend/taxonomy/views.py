from rest_framework import viewsets
from .models import Industry, Category, Subcategory
from .serializers import IndustrySerializer, CategorySerializer, SubcategorySerializer

class IndustryViewSet(viewsets.ModelViewSet):
    queryset = Industry.objects.all().order_by('-id') if hasattr(Industry, 'id') else Industry.objects.all()
    serializer_class = IndustrySerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('-id') if hasattr(Category, 'id') else Category.objects.all()
    serializer_class = CategorySerializer

class SubcategoryViewSet(viewsets.ModelViewSet):
    queryset = Subcategory.objects.all().order_by('-id') if hasattr(Subcategory, 'id') else Subcategory.objects.all()
    serializer_class = SubcategorySerializer
