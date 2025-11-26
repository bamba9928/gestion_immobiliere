from rest_framework import serializers

from apps.core.models import Bien


class BienSerializer(serializers.ModelSerializer):
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

    def get_loyer_mensuel(self, obj):
        return int(obj.loyer_ref)

    def get_disponibilite(self, obj):
        return {
            'est_disponible': obj.est_disponible,
            'label': 'Disponible' if obj.est_disponible else 'Occupé',
        }
