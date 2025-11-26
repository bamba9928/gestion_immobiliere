"""
API views exposing a subset of the domain model to mobile clients.

Currently only lists available and active properties. Authentication
is required to access the endpoints.
"""
from rest_framework import generics, permissions

from apps.core.models import Bien
from .serializers import BienSerializer


class MobileBienListView(generics.ListAPIView):
    """List API view returning available and active properties."""
    queryset = Bien.objects.filter(est_actif=True, disponible=True).order_by('-created_at')
    serializer_class = BienSerializer
    permission_classes = [permissions.IsAuthenticated]
