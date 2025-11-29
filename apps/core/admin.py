from django.contrib import admin
from django.utils.html import format_html
from .models import Bien, Bail, Loyer


admin.site.site_header = "MADA IMMO Administration"
admin.site.site_title = "MADA IMMO"
admin.site.index_title = "Pilotage de l'agence"


class DisponibiliteFilter(admin.SimpleListFilter):
    title = "Disponibilité"
    parameter_name = "disponibilite"

    def lookups(self, request, model_admin):
        return (
            ("disponible", "Disponible"),
            ("occupe", "Occupé"),
        )

    def queryset(self, request, queryset):
        # On réutilise le manager métier
        if self.value() == "disponible":
            return queryset.disponibles()
        if self.value() == "occupe":
            return queryset.occupes()
        return queryset


@admin.register(Bien)
class BienAdmin(admin.ModelAdmin):
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
        DisponibiliteFilter,   # 🔎 filtre métier
    )
    search_fields = ("titre", "adresse", "ville")
    list_per_page = 20

    def etat_badge(self, obj):
        if obj.est_occupe:
            return format_html(
                '<span style="color:red; font-weight:bold;">OCCUPÉ</span>'
            )
        return format_html(
            '<span style="color:green; font-weight:bold;">DISPONIBLE</span>'
        )

    etat_badge.short_description = "État"

    def disponible_colonne(self, obj):
        # Utilise la propriété calculée est_disponible
        return obj.est_disponible

    disponible_colonne.boolean = True
    disponible_colonne.short_description = "Disponible ?"

@admin.register(Bail)
class BailAdmin(admin.ModelAdmin):
    list_display = ('locataire', 'bien', 'date_debut', 'date_fin', 'loyer_total', 'est_signe_badge')
    list_filter = ('est_signe', 'date_fin')
    search_fields = ('locataire__username', 'locataire__last_name', 'bien__titre')
    date_hierarchy = 'date_debut'
    autocomplete_fields = ['bien', 'locataire']

    def est_signe_badge(self, obj):
        return obj.est_signe

    est_signe_badge.boolean = True  # Affiche une icône (check/croix)
    est_signe_badge.short_description = "Signé"


@admin.register(Loyer)
class LoyerAdmin(admin.ModelAdmin):
    list_display = ('bail_info', 'periode_fmt', 'montant_du', 'statut_badge', 'date_paiement')
    list_filter = ('statut', 'periode_debut')
    search_fields = ('bail__locataire__username', 'bail__bien__titre')

    def bail_info(self, obj):
        return f"{obj.bail.locataire.last_name} ({obj.bail.bien.titre})"

    bail_info.short_description = "Locataire / Bien"

    def periode_fmt(self, obj):
        return obj.periode_debut.strftime('%B %Y')

    periode_fmt.short_description = "Période"

    def statut_badge(self, obj):
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

    statut_badge.short_description = "Statut"