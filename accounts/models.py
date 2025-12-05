from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
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

    class Meta:
        verbose_name = _("Utilisateur")
        verbose_name_plural = _("Utilisateurs")

    def __str__(self) -> str:
        full_name = self.get_full_name()
        return f"{full_name} ({self.username})" if full_name else self.username

    # -------------------------------
    #   PROPRIÉTÉS KYC POUR L'ADMIN
    # -------------------------------

    @property
    def piece_identite(self):
        """
        Utilisé par LocataireKycMixin.pieces_locataire.
        On le mappe sur profile.cni_scan pour éviter de dupliquer le fichier.
        """
        profile = getattr(self, "profile", None)
        return getattr(profile, "cni_scan", None) if profile else None

    @property
    def justificatif_domicile(self):
        """
        Utilisé par LocataireKycMixin.pieces_locataire.
        On le mappe sur profile.justificatif_domicile.
        """
        profile = getattr(self, "profile", None)
        return getattr(profile, "justificatif_domicile", None) if profile else None

    @property
    def kyc_verified(self) -> bool:
        """
        Utilisé par LocataireKycMixin.locataire_kyc.
        Règle simple : KYC vérifié si CNI + justificatif présents.
        """
        profile = getattr(self, "profile", None)
        if not profile:
            return False
        return bool(profile.cni_scan and profile.justificatif_domicile)

    def kyc_status_display(self) -> str:
        """
        Utilisé par LocataireKycMixin.locataire_kyc.
        Renvoie une chaîne lisible (Incomplet / En cours / Vérifié).
        """
        profile = getattr(self, "profile", None)
        if not profile:
            return "Incomplet"

        has_cni = bool(profile.cni_scan)
        has_justif = bool(profile.justificatif_domicile)

        if has_cni and has_justif:
            return "Vérifié"
        if has_cni or has_justif:
            return "En cours"
        return "Incomplet"


class UserProfile(models.Model):
    """
    Extension du CustomUser pour les infos bail / KYC.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )

    telephone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Numéro de téléphone principal (profil)."
    )
    adresse_postale = models.TextField(
        blank=True,
        help_text="Adresse permanente (avant emménagement)."
    )

    # Infos CNI / identité
    cni_numero = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Numéro CNI/Passeport",
    )
    cni_scan = models.FileField(
        upload_to='users/cni/',
        blank=True,
        null=True,
        verbose_name="Scan CNI/Passeport",
    )

    # Justificatif de domicile pour le KYC
    justificatif_domicile = models.FileField(
        upload_to='users/justificatifs_domicile/',
        blank=True,
        null=True,
        verbose_name="Justificatif de domicile",
    )

    # Agent ou non
    is_agent = models.BooleanField(
        default=False,
        help_text="Cochez si cet utilisateur est un agent immobilier",
    )

    def __str__(self):
        return f"Profil de {self.user.username}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Crée automatiquement le profil à la création du CustomUser
    et le sauvegarde à chaque mise à jour.
    """
    if created:
        UserProfile.objects.create(user=instance)
    if hasattr(instance, "profile"):
        instance.profile.save()
