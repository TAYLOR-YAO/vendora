from rest_framework import viewsets
from .models import GatewayAccount, Payment, Refund, Payout
from .serializers import GatewayAccountSerializer, PaymentSerializer, RefundSerializer, PayoutSerializer

class GatewayAccountViewSet(viewsets.ModelViewSet):
    queryset = GatewayAccount.objects.all().order_by('-id') if hasattr(GatewayAccount, 'id') else GatewayAccount.objects.all()
    serializer_class = GatewayAccountSerializer

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().order_by('-id') if hasattr(Payment, 'id') else Payment.objects.all()
    serializer_class = PaymentSerializer

class RefundViewSet(viewsets.ModelViewSet):
    queryset = Refund.objects.all().order_by('-id') if hasattr(Refund, 'id') else Refund.objects.all()
    serializer_class = RefundSerializer

class PayoutViewSet(viewsets.ModelViewSet):
    queryset = Payout.objects.all().order_by('-id') if hasattr(Payout, 'id') else Payout.objects.all()
    serializer_class = PayoutSerializer
