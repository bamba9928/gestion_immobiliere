from rest_framework import generics, permissions
from apps.core.models import Bien
from .serializers import BienSerializer
from apps.core.models import Intervention
from .serializers import InterventionSerializer

class MobileBienListView(generics.ListAPIView):
    """
    Endpoint mobile pour lister les biens disponibles.
    Accessible sans authentification pour la vitrine.
    """
    serializer_class = BienSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        # Version simple : tous les biens disponibles
        return (
            Bien.objects.disponibles()
            .order_by('-created_at')
        )
class BienDetailView(generics.RetrieveAPIView):
    serializer_class = BienSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        # On limite aux biens actifs
        return Bien.objects.filter(est_actif=True)

class InterventionCreateView(generics.CreateAPIView):
    queryset = Intervention.objects.all()
    serializer_class = InterventionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # On lie automatiquement le locataire et son biens actuel
        user = self.request.user
        # On suppose ici une logique simple où le user a un bail actif
        bail = user.baux.filter(est_signe=True).first()
        if bail:
            serializer.save(locataire=user, bien=bail.bien)
        else:
            # Gérer l'erreur si pas de bail
            pass
class InterventionListCreateView(generics.ListCreateAPIView):
    serializer_class = InterventionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Retourne uniquement les interventions du locataire connecté
        return Intervention.objects.filter(locataire=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        # Associe automatiquement le locataire et son biens
        user = self.request.user
        # On cherche le bail actif
        bail = user.baux.filter(est_signe=True).first()

        if bail:
            serializer.save(locataire=user, bien=bail.bien)
        else:

            pass