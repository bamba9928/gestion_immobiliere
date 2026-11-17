from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse

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

    def piece_identite_link(self, obj: CustomUser) -> str:
        """Affiche un lien sécurisé vers la pièce d'identité."""
        if not obj.piece_identite:
            return "—"
        url = reverse('download_kyc', args=[obj.id, 'cni'])
        return format_html('<a href="{}" target="_blank" rel="noopener">📄 Pièce (Sécurisé)</a>', url)

    def justificatif_domicile_link(self, obj: CustomUser) -> str:
        """Affiche un lien sécurisé vers le justificatif de domicile."""
        if not obj.justificatif_domicile:
            return "—"
        url = reverse('download_kyc', args=[obj.id, 'justificatif'])
        return format_html('<a href="{}" target="_blank" rel="noopener">🏠 Justif. (Sécurisé)</a>', url)

    piece_identite_link.short_description = "Pièce ID"
    justificatif_domicile_link.short_description = "Justif. domicile"