from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import IsTenant
from apps.core.models import Bien, Intervention
from apps.core.permissions import get_active_bail
from .serializers import (
    BienSerializer,
    InterventionSerializer,
    BailSerializer,
)


class BienListView(generics.ListAPIView):
    """
    Liste publique des biens disponibles.
    Accessible sans authentification pour la vitrine.
    """
    serializer_class = BienSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Bien.objects.disponibles().order_by("-created_at")


class BienDetailView(generics.RetrieveAPIView):
    """
    Détail public d'un bien actif.
    Utilise la même logique que la liste pour la cohérence.
    """
    serializer_class = BienSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        # Utilise disponibles() pour rester cohérent avec la liste
        return Bien.objects.disponibles()


class InterventionListCreateView(generics.ListCreateAPIView):
    """
    Endpoint pour lister et créer des interventions.
    - GET : liste les interventions du locataire connecté
    - POST : crée une nouvelle intervention (auto-associe le bail/bien)
    """
    serializer_class = InterventionSerializer
    permission_classes = [IsTenant]

    def get_queryset(self):
        user = self.request.user
        return (
            Intervention.objects
            .filter(locataire=user)
            .select_related("bien")   # utile pour réduire les requêtes
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        user = self.request.user

        # Utilise la fonction centrale get_active_bail pour éviter de dupliquer la logique
        bail = get_active_bail(user)
        if not bail:
            raise PermissionDenied("Aucun bail actif trouvé pour ce locataire.")

        serializer.save(locataire=user, bien=bail.bien)
class MyBailView(APIView):
    permission_classes = [IsTenant]

    def get(self, request):
        bail = get_active_bail(request.user)
        if not bail:
            return Response({"error": "Aucun bail actif"}, status=404)

        serializer = BailSerializer(bail)
        return Response(serializer.data)

