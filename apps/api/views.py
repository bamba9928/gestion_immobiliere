from rest_framework import generics, permissions

from apps.core.models import Bien
from .serializers import BienSerializer


class MobileBienListView(generics.ListAPIView):
    queryset = Bien.objects.filter(est_actif=True, disponible=True).order_by('-created_at')
    serializer_class = BienSerializer
    permission_classes = [permissions.IsAuthenticated]
    from rest_framework import generics, permissions
    from apps.core.models import Bien
    from .serializers import BienSerializer

    class BienListAPIView(generics.ListAPIView):
        """
        Endpoint mobile pour lister les biens disponibles.
        Accessible sans authentification pour la vitrine.
        """
        queryset = Bien.objects.filter(est_disponible=True, est_archive=False)
        serializer_class = BienSerializer
        permission_classes = [permissions.AllowAny]

