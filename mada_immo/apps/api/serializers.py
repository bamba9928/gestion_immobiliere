"""
Serializers for the API layer of the MADA IMMO project.

The serializers translate Django model instances into JSON
representations suitable for consumption by mobile clients. To keep
payloads concise, derived fields are exposed using `SerializerMethodField`.
"""
from rest_framework import serializers

from apps.core.models import Bien


class BienSerializer(serializers.ModelSerializer):
    """Serialize a Bien instance for consumption by the mobile API."""
    loyer_mensuel = serializers.SerializerMethodField()
    disponibilite = serializers.SerializerMethodField()

    class Meta:
        model = Bien
        fields = [
            'id',
            'titre',
            'type_bien',
            'ville',
            'adresse',
            'surface',
            'nb_pieces',
            'loyer_mensuel',
            'charges_ref',
            'disponibilite',
            'est_actif',
            'created_at',
        ]

    def get_loyer_mensuel(self, obj: Bien) -> int:
        """Return the reference rent as an integer."""
        return int(obj.loyer_ref)

    def get_disponibilite(self, obj: Bien) -> dict[str, object]:
        """Return a dictionary describing availability status for the property."""
        return {
            'est_disponible': obj.est_disponible,
            'label': 'Disponible' if obj.est_disponible else 'Occupé',
        }
