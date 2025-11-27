from rest_framework import serializers
from apps.core.models import Bien
from apps.core.models import Intervention

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
class InterventionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Intervention
        fields = ['id', 'bien', 'objet', 'description', 'photo_avant', 'statut', 'created_at']
        read_only_fields = ['statut', 'bien'] # Le locataire ne décide pas du statut
class InterventionSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = Intervention
        fields = [
            'id',
            'objet',
            'description',
            'photo_avant',
            'statut',
            'statut_display',
            'created_at'
        ]
        read_only_fields = ['statut', 'created_at']