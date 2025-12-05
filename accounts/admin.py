from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "kyc_verified",      # OK en list_display (propriété)
        "kyc_status_display" # OK aussi
    )

    # NE PAS mettre kyc_verified ici
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "groups",
    )

    # NE PAS mettre kyc_verified_at ici si le champ n'existe pas
    readonly_fields = ()

    fieldsets = UserAdmin.fieldsets + (
        ("Infos supplémentaires", {"fields": ("phone_number", "address")}),
    )

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