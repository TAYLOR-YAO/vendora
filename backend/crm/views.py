from rest_framework import viewsets
from .models import Customer, Contact, Pipeline, Opportunity, Activity
from .serializers import CustomerSerializer, ContactSerializer, PipelineSerializer, OpportunitySerializer, ActivitySerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all().order_by('-id') if hasattr(Customer, 'id') else Customer.objects.all()
    serializer_class = CustomerSerializer

class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all().order_by('-id') if hasattr(Contact, 'id') else Contact.objects.all()
    serializer_class = ContactSerializer

class PipelineViewSet(viewsets.ModelViewSet):
    queryset = Pipeline.objects.all().order_by('-id') if hasattr(Pipeline, 'id') else Pipeline.objects.all()
    serializer_class = PipelineSerializer

class OpportunityViewSet(viewsets.ModelViewSet):
    queryset = Opportunity.objects.all().order_by('-id') if hasattr(Opportunity, 'id') else Opportunity.objects.all()
    serializer_class = OpportunitySerializer

class ActivityViewSet(viewsets.ModelViewSet):
    queryset = Activity.objects.all().order_by('-id') if hasattr(Activity, 'id') else Activity.objects.all()
    serializer_class = ActivitySerializer
