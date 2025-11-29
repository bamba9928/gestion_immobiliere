from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from apps.api.permissions import IsTenant
from apps.core.models import Bien, Intervention
from .serializers import BienSerializer, InterventionSerializer
class BienListView(generics.ListAPIView):
    """
    Liste publique des biens disponibles.
    Accessible sans authentification pour la vitrine.
    """
    serializer_class = BienSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Bien.objects.disponibles().order_by('-created_at')


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
            .select_related('bien')   # optionnel mais utile pour réduire les requêtes
            .order_by('-created_at')
        )

    def perform_create(self, serializer):
        user = self.request.user
        today = timezone.now().date()

        # Récupération sécurisée du bail actif avec select_related sur le bien
        bail = (
            user.baux
            .filter(
                est_signe=True,
                date_debut__lte=today,
                date_fin__gte=today,
            )
            .select_related('bien')
            .first()
        )

        if not bail:
            raise PermissionDenied("Aucun bail actif trouvé pour ce locataire.")

        # Une seule sauvegarde, sans doublon
        serializer.save(locataire=user, bien=bail.bien)
