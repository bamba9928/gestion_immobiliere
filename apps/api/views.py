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
    # On filtre sur 'est_actif' (champ réel) et 'disponible'
    queryset = Bien.objects.filter(est_actif=True, disponible=True).order_by('-created_at')
    serializer_class = BienSerializer
    # AllowAny permet à l'app mobile d'afficher les biens sans que l'utilisateur soit connecté
    permission_classes = [permissions.AllowAny]
class BienDetailView(generics.RetrieveAPIView):
    queryset = Bien.objects.filter(est_actif=True)
    serializer_class = BienSerializer
    permission_classes = [permissions.AllowAny]
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