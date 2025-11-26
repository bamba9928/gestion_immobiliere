"""
Models for the core application of the MADA IMMO platform.

This module defines the primary entities used to represent properties
(biens), leases (baux), rent invoices (loyers), public announcements
(annonces) and maintenance interventions. The design follows the
requirements laid out in the project specification, including
properties and convenience methods for common business logic.
"""
from datetime import date
from django.conf import settings
from django.db import models


class Bien(models.Model):
    """
    Represents a real estate asset (apartment, house, shop or land).
    Each property can be associated with multiple leases and
    advertisements and may optionally include a principal photo.
    """

    TYPE_CHOICES = [
        ('APPARTEMENT', 'Appartement'),
        ('MAISON', 'Maison'),
        ('COMMERCE', 'Local Commercial'),
        ('TERRAIN', 'Terrain'),
    ]

    # Infos principales
    titre = models.CharField(max_length=200, help_text="Ex: T3 Centre Ville - Résidence Mada")
    type_bien = models.CharField(max_length=20, choices=TYPE_CHOICES, default='APPARTEMENT')
    adresse = models.TextField()
    ville = models.CharField(max_length=100, default='Dakar')

    # Caractéristiques
    surface = models.PositiveIntegerField(help_text="En m²")
    nb_pieces = models.PositiveIntegerField(verbose_name="Nombre de pièces", default=1)
    description = models.TextField(blank=True)

    # Financier
    loyer_ref = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name="Loyer de référence (FCFA/Ar)",
    )
    charges_ref = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        verbose_name="Charges estimées",
    )
    disponible = models.BooleanField(
        default=True,
        help_text="Disponible immédiatement tant qu'aucun bail actif n'est en cours",
    )

    # Gestion
    proprietaire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='biens_possedes',
    )
    photo_principale = models.ImageField(upload_to='biens/', blank=True, null=True)
    est_actif = models.BooleanField(
        default=True,
        help_text="Décochez si le bien est vendu ou retiré de la gestion",
    )

    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bien Immobilier"
        verbose_name_plural = "Biens Immobiliers"

    def __str__(self) -> str:
        return f"{self.get_type_bien_display()} - {self.titre}"

    @property
    def est_occupe(self) -> bool:
        """Return True if an active lease exists for this property."""
        return self.baux.filter(date_fin__gte=date.today(), est_signe=True).exists()

    @property
    def est_disponible(self) -> bool:
        """Return True if the property is active, marked available and not occupied."""
        return self.est_actif and self.disponible and not self.est_occupe


class Bail(models.Model):
    """Represents a lease binding a property and a tenant."""

    bien = models.ForeignKey(Bien, on_delete=models.PROTECT, related_name='baux')
    locataire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='baux',
    )

    # Dates clés
    date_debut = models.DateField()
    date_fin = models.DateField()

    # Financier (Gelé à la signature du bail)
    montant_loyer = models.DecimalField(max_digits=10, decimal_places=0)
    montant_charges = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    depot_garantie = models.DecimalField(max_digits=10, decimal_places=0)
    jour_paiement = models.PositiveIntegerField(
        default=5,
        help_text="Jour du mois limite pour payer (ex: le 5)",
    )

    # État du dossier
    est_signe = models.BooleanField(default=False)
    fichier_contrat = models.FileField(
        upload_to='baux_signes/', blank=True, null=True, help_text="PDF signé",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bail / Contrat"
        verbose_name_plural = "Baux"
        ordering = ['-date_debut']

    def __str__(self) -> str:
        return f"Bail {self.locataire.last_name} - {self.bien.titre}"

    def loyer_total(self) -> int:
        """Return the monthly rent plus charges."""
        return int(self.montant_loyer + self.montant_charges)

    def save(self, *args, **kwargs) -> None:
        """
        Save the lease and update the availability of the associated property.

        When a lease is created or updated, the associated property's
        ``disponible`` flag is synchronised based on whether there are any
        active, signed leases. A property becomes unavailable as soon as a
        lease is signed and its end date is in the future; conversely it
        becomes available again once all active leases have finished. This
        logic ensures that the ``Bien.est_disponible`` property reported via
        the API and admin accurately reflects real‐time availability without
        requiring manual toggles by administrators or owners.
        """
        super().save(*args, **kwargs)
        # Determine if this lease makes the property unavailable
        bien = self.bien
        # If this lease is signed and still active, mark property as unavailable
        if self.est_signe and self.date_fin >= date.today():
            if bien.disponible:
                bien.disponible = False
                bien.save(update_fields=['disponible'])
        else:
            # If there are no other active signed leases, mark property available
            from apps.core.models import Bail  # local import to avoid circular import at module load
            active_baux = Bail.objects.filter(
                bien=bien,
                est_signe=True,
                date_fin__gte=date.today(),
            ).exclude(pk=self.pk)
            if not active_baux.exists() and not bien.disponible:
                bien.disponible = True
                bien.save(update_fields=['disponible'])


class Loyer(models.Model):
    """
    Represents a monthly rent invoice. Invoices are generated automatically
    based on the lease information and track payment status.
    """

    STATUT_CHOICES = [
        ('A_PAYER', 'À payer'),
        ('PARTIEL', 'Paiement partiel'),
        ('PAYE', 'Payé'),
        ('RETARD', 'En retard'),
    ]

    bail = models.ForeignKey(Bail, on_delete=models.PROTECT, related_name='loyers')

    # Période concernée
    periode_debut = models.DateField()
    periode_fin = models.DateField()
    date_echeance = models.DateField(help_text="Date limite de paiement")

    # Montants
    montant_du = models.DecimalField(max_digits=10, decimal_places=0)
    montant_verse = models.DecimalField(max_digits=10, decimal_places=0, default=0)

    # Suivi
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='A_PAYER')
    date_paiement = models.DateTimeField(null=True, blank=True)

    # Documents
    quittance = models.FileField(upload_to='quittances/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Loyer / Échéance"
        verbose_name_plural = "Loyers"
        unique_together = ('bail', 'periode_debut')  # Un seul loyer par mois pour un bail

    def __str__(self) -> str:
        return f"{self.bail.locataire.username} - {self.periode_debut.strftime('%B %Y')}"

    @property
    def reste_a_payer(self) -> int:
        """Return the remaining amount due for this invoice."""
        return int(self.montant_du - self.montant_verse)

    @property
    def est_en_retard(self) -> bool:
        """Return True if the payment due date has passed and the invoice isn't paid."""
        return self.statut != 'PAYE' and date.today() > self.date_echeance


class Annonce(models.Model):
    """
    Public advertisement for a property. Annonce objects follow a simple
    workflow from draft to publication. Pricing is captured separately
    from the reference rent to allow the owner to adjust marketing
    information without affecting existing leases.
    """

    STATUT_CHOICES = [
        ('BROUILLON', 'Brouillon'),
        ('ATTENTE', 'En attente'),
        ('PUBLIE', 'Publiée'),
        ('ARCHIVE', 'Archivée'),
    ]

    bien = models.ForeignKey(Bien, on_delete=models.PROTECT, related_name='annonces')
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    prix = models.DecimalField(max_digits=10, decimal_places=0)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='BROUILLON')
    date_publication = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Annonce"
        verbose_name_plural = "Annonces"
        ordering = ['-date_publication']

    def __str__(self) -> str:
        return f"{self.bien} - {self.get_statut_display()}"


class Intervention(models.Model):
    """
    Maintenance or repair request linked to a property. Tenants can
    submit a request, which is then assigned to an agent. Before and
    after photos may be attached to illustrate the intervention.
    """

    STATUT_CHOICES = [
        ('NOUVEAU', 'Nouveau'),
        ('EN_COURS', 'En cours'),
        ('RESOLU', 'Résolu'),
    ]

    bien = models.ForeignKey(Bien, on_delete=models.PROTECT, related_name='interventions')
    locataire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='interventions',
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='interventions_assignees',
        null=True,
        blank=True,
    )
    objet = models.CharField(max_length=200)
    description = models.TextField()
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='NOUVEAU')
    photo_avant = models.ImageField(upload_to='interventions/avant/', null=True, blank=True)
    photo_apres = models.ImageField(upload_to='interventions/apres/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Intervention"
        verbose_name_plural = "Interventions"
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.objet} - {self.get_statut_display()}"
