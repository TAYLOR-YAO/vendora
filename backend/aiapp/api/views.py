# This file was auto-generated as a scaffold.
# SAFE to edit. Keep functions/class names if you rely on them across apps.

from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from rest_framework.views import APIView

# Example ViewSet (uncomment and adjust to your model/serializer)
# from .models import ModelName
# from .serializers import ModelNameSerializer
# from .permissions import IsStaffOrReadOnly
#
# class ModelNameViewSet(viewsets.ModelViewSet):
#     queryset = ModelName.objects.all()
#     serializer_class = ModelNameSerializer
#     permission_classes = [IsStaffOrReadOnly]

class HealthView(APIView):
    """Simple health endpoint per-app."""
    authentication_classes = []
    permission_classes = []
    def get(self, request, *args, **kwargs):
        return Response({"status": "ok", "app": __package__.split('.')[0]}, status=status.HTTP_200_OK)
