from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Configuration de l'administration pour le modèle CustomUser.
    Gère l'affichage et l'édition des informations KYC.
    """

    # Champs affichés dans le formulaire d'édition
    fieldsets = UserAdmin.fieldsets + (
        (
            "KYC & informations locataire",
            {
                "fields": (
                    "phone_number",
                    "address",
                    "kyc_verified",
                    "kyc_verified_at",
                    "piece_identite",
                    "justificatif_domicile",
                )
            },
        ),
    )

    # Champs affichés dans le formulaire de création
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "KYC & informations locataire",
            {
                "classes": ("wide",),
                "fields": (
                    "phone_number",
                    "address",
                    "piece_identite",
                    "justificatif_domicile",
                ),
            },
        ),
    )

    # Colonnes affichées dans la liste
    list_display = (
        "username",
        "email",
        "last_name",
        "first_name",
        "is_active",
        "kyc_badge",
        "piece_identite_link",
        "justificatif_domicile_link",
    )

    # Filtres disponibles
    list_filter = UserAdmin.list_filter + ("kyc_verified",)

    # Champs en lecture seule
    readonly_fields = ("kyc_verified_at",)

    def kyc_badge(self, obj: CustomUser) -> str:
        """
        Affiche un badge coloré indiquant le statut KYC.
        """
        color = "green" if obj.kyc_verified else "orange"
        label = obj.kyc_status_display()
        return format_html('<strong style="color:{};">{}</strong>', color, label)

    kyc_badge.short_description = "KYC"
    kyc_badge.admin_order_field = "kyc_verified"  # Permet le tri

    def _file_link(self, file_field, label: str) -> str:
        """
        Méthode utilitaire pour générer un lien vers un fichier.
        """
        if not file_field:
            return "—"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">{}</a>',
            file_field.url,
            label
        )

    def piece_identite_link(self, obj: CustomUser) -> str:
        """
        Affiche un lien vers la pièce d'identité.
        """
        return self._file_link(obj.piece_identite, "📄 Pièce")

    piece_identite_link.short_description = "Pièce ID"

    def justificatif_domicile_link(self, obj: CustomUser) -> str:
        """
        Affiche un lien vers le justificatif de domicile.
        """
        return self._file_link(obj.justificatif_domicile, "🏠 Justif.")

    justificatif_domicile_link.short_description = "Justif. domicile"