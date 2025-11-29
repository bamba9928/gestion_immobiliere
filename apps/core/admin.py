from django.contrib import admin
from django.utils.html import format_html
from .models import Bien, Bail, Loyer

# Configuration de l'interface admin
admin.site.site_header = "MADA IMMO Administration"
admin.site.site_title = "MADA IMMO"
admin.site.index_title = "Pilotage de l'agence"


class DisponibiliteFilter(admin.SimpleListFilter):
    """Filtre personnalisé pour la disponibilité des biens."""

    title = "Disponibilité"
    parameter_name = "disponibilite"

    def lookups(self, request, model_admin):
        return (
            ("disponible", "Disponible"),
            ("occupe", "Occupé"),
        )

    def queryset(self, request, queryset):
        if self.value() == "disponible":
            return queryset.disponibles()
        if self.value() == "occupe":
            return queryset.occupes()
        return queryset


class LocataireKycMixin:
    """Mixin pour afficher le statut KYC et les documents d'un locataire."""

    @staticmethod
    def _get_locataire(obj):
        """Récupère l'instance du locataire."""
        if hasattr(obj, 'locataire'):
            return obj.locataire
        if hasattr(obj, 'bail'):
            return obj.bail.locataire
        return None

    @staticmethod
    def _file_link(file_field, label):
        """Génère un lien HTML sécurisé vers un fichier."""
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
            file_field.url,
            label
        )

    @admin.display(description="KYC")
    def locataire_kyc(self, obj):
        """Affiche le statut KYC avec un badge coloré."""
        locataire = self._get_locataire(obj)
        if not locataire:
            return "—"

        status = getattr(locataire, "kyc_status_display", lambda: "")()
        color = "green" if getattr(locataire, "kyc_verified", False) else "orange"
        return format_html('<strong style="color:{};">{}</strong>', color, status or "—")

    @admin.display(description="Pièces")
    def pieces_locataire(self, obj):
        """Affiche les liens vers les documents du locataire."""
        locataire = self._get_locataire(obj)
        if not locataire:
            return "—"

        pieces = []
        if getattr(locataire, "piece_identite", None):
            pieces.append(self._file_link(locataire.piece_identite, "Pièce"))
        if getattr(locataire, "justificatif_domicile", None):
            pieces.append(self._file_link(locataire.justificatif_domicile, "Justif."))

        return format_html(" / ".join(pieces)) if pieces else "—"


@admin.register(Bien)
class BienAdmin(admin.ModelAdmin):
    """Administration des biens immobiliers."""

    list_display = (
        "titre",
        "type_bien",
        "ville",
        "loyer_ref",
        "etat_badge",
        "disponible_colonne",
        "est_actif",
    )
    list_filter = (
        "type_bien",
        "ville",
        "est_actif",
        DisponibiliteFilter,
    )
    search_fields = ("titre", "adresse", "ville")
    list_per_page = 20

    @admin.display(description="État")
    def etat_badge(self, obj):
        """Affiche un badge indiquant l'état du bien."""
        color = "red" if obj.est_occupe else "green"
        text = "OCCUPÉ" if obj.est_occupe else "DISPONIBLE"
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            color,
            text
        )

    @admin.display(description="Disponible ?", boolean=True)
    def disponible_colonne(self, obj):
        """Retourne l'état de disponibilité sous forme d'icône."""
        return obj.est_disponible


@admin.register(Bail)
class BailAdmin(admin.ModelAdmin, LocataireKycMixin):
    """Administration des baux."""

    list_display = (
        'bien',
        'locataire',
        'locataire_kyc',
        'pieces_locataire',
        'date_debut',
        'date_fin',
        'loyer_total',
        'est_signe_badge',
    )
    list_filter = ('est_signe', 'date_fin')
    search_fields = ('locataire__username', 'locataire__last_name', 'bien__titre')
    date_hierarchy = 'date_debut'
    autocomplete_fields = ['bien', 'locataire']

    @admin.display(description="Signé", boolean=True)
    def est_signe_badge(self, obj):
        """Affiche le statut de signature sous forme d'icône."""
        return obj.est_signe


@admin.register(Loyer)
class LoyerAdmin(admin.ModelAdmin, LocataireKycMixin):
    """Administration des loyers."""

    list_display = (
        'bail_info',
        'locataire_kyc',
        'pieces_locataire',
        'periode_fmt',
        'montant_du',
        'statut_badge',
        'date_paiement',
    )
    list_filter = ('statut', 'periode_debut')
    search_fields = ('bail__locataire__username', 'bail__bien__titre')

    @admin.display(description="Locataire / Bien")
    def bail_info(self, obj):
        """Affiche les informations du bail associé."""
        return f"{obj.bail.locataire.last_name} ({obj.bail.bien.titre})"

    @admin.display(description="Période")
    def periode_fmt(self, obj):
        """Formate la période sous forme lisible."""
        return obj.periode_debut.strftime('%B %Y')

    @admin.display(description="Statut")
    def statut_badge(self, obj):
        """Affiche le statut de paiement avec un badge coloré."""
        colors = {
            'A_PAYER': 'orange',
            'PAYE': 'green',
            'RETARD': 'red',
            'PARTIEL': 'blue',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.statut, 'black'),
            obj.get_statut_display()
        )