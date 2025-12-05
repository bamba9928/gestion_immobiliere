from apps.core.models import Intervention, Bien, Bail
from rest_framework import serializers
from rest_framework import serializers

from apps.core.models import Intervention, Bien, Bail


class BienSerializer(serializers.ModelSerializer):
    loyer_mensuel = serializers.SerializerMethodField(read_only=True)
    disponibilite = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Bien
        fields = [
            "id",
            "titre",
            "type_bien",
            "ville",
            "adresse",
            "surface",
            "nb_pieces",
            "loyer_mensuel",
            "charges_ref",
            "disponibilite",
            "est_actif",
            "created_at",
        ]

    def get_loyer_mensuel(self, obj):
        """
        Renvoie le loyer mensuel en int si possible, sinon la valeur brute.
        Gère aussi le cas où loyer_ref est None.
        """
        value = getattr(obj, "loyer_ref", None)
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            # Si c'est un Decimal ou autre, on renvoie la valeur telle quelle
            return value

    def get_disponibilite(self, obj):
        return {
            "est_disponible": bool(obj.est_disponible),
            "label": "Disponible" if obj.est_disponible else "Occupé",
        }


class InterventionSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(
        source="get_statut_display",
        read_only=True,
    )

    class Meta:
        model = Intervention
        fields = [
            "id",
            "objet",
            "description",
            "photo_avant",
            "statut",
            "statut_display",
            "created_at",
        ]
        # statut fixé en lecture seule côté API si on gères le changement de statut ailleurs
        read_only_fields = ["statut", "created_at"]
class BailSerializer(serializers.ModelSerializer):
    bien_titre = serializers.CharField(source="bien.titre", read_only=True)
    bien_adresse = serializers.CharField(source="bien.adresse", read_only=True)
    bien_ville = serializers.CharField(source="bien.ville", read_only=True)
    proprietaire_nom = serializers.CharField(
        source="bien.proprietaire.get_full_name", read_only=True
    )
    locataire_nom = serializers.CharField(
        source="locataire.get_full_name", read_only=True
    )
    loyer_mensuel = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Bail
        fields = [
            "id",
            # Infos bien
            "bien_titre",
            "bien_adresse",
            "bien_ville",
            "proprietaire_nom",
            # Locataire
            "locataire_nom",
            # Données bail
            "montant_loyer",
            "montant_charges",
            "loyer_mensuel",
            "depot_garantie",
            "jour_paiement",
            "date_debut",
            "date_fin",
            "est_signe",
            "fichier_contrat",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "bien_titre",
            "bien_adresse",
            "bien_ville",
            "proprietaire_nom",
            "locataire_nom",
            "loyer_mensuel",
            "created_at",
        ]

    def get_loyer_mensuel(self, obj):
        """
        Utilise la méthode métier loyer_total() du modèle Bail.
        """
        try:
            return int(obj.loyer_total())
        except Exception:
            return int(obj.montant_loyer + obj.montant_charges)
