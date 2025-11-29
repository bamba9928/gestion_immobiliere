from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    phone_number = models.CharField(
        max_length=30,
        blank=True,
        verbose_name=_("Téléphone"),
        help_text=_("Numéro de téléphone principal de l'utilisateur."),
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Adresse"),
    )
    kyc_verified = models.BooleanField(
        default=False,
        verbose_name=_("KYC vérifié"),
    )
    piece_identite = models.FileField(
        upload_to="kyc/pieces/",
        blank=True,  # blank=True suffit, null n'est pas recommandé pour FileField
        verbose_name=_("Pièce d'identité"),
    )
    justificatif_domicile = models.FileField(
        upload_to="kyc/domicile/",
        blank=True,
        verbose_name=_("Justificatif de domicile"),
    )
    kyc_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date de vérification"),
    )

    class Meta:
        verbose_name = _("Utilisateur")
        verbose_name_plural = _("Utilisateurs")

    def __str__(self) -> str:
        full_name = self.get_full_name()
        return f"{full_name} ({self.username})" if full_name else self.username

    def kyc_status_display(self) -> str:
        """
        Retourne un libellé simple pour l'affichage du statut KYC.
        """
        return "Vérifié" if self.kyc_verified else "En attente"
