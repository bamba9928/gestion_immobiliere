from datetime import date

from django.conf import settings
from django.db import models


class Bien(models.Model):
    """
    Représente un bien immobilier (Appartement, Maison, Terrain/Local).
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
    loyer_ref = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="Loyer de référence (FCFA/Ar)")
    charges_ref = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="Charges estimées")
    disponible = models.BooleanField(
        default=True,
        help_text="Disponible immédiatement tant qu'aucun bail actif n'est en cours",
    )

    # Gestion
    proprietaire = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='biens_possedes')
    photo_principale = models.ImageField(upload_to='biens/', blank=True, null=True)
    est_actif = models.BooleanField(default=True, help_text="Décocher si le bien est vendu ou retiré de la gestion")

    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bien Immobilier"
        verbose_name_plural = "Biens Immobiliers"

    def __str__(self):
        return f"{self.get_type_bien_display()} - {self.titre}"

    @property
    def est_occupe(self):
        # Retourne True si un bail actif existe
        return self.baux.filter(date_fin__gte=date.today(), est_signe=True).exists()

    @property
    def est_disponible(self):
        return self.est_actif and self.disponible and not self.est_occupe


class Bail(models.Model):
    """
    Le contrat liant un Bien et un Locataire.
    """
    bien = models.ForeignKey(Bien, on_delete=models.PROTECT, related_name='baux')
    locataire = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='baux')

    # Dates clés
    date_debut = models.DateField()
    date_fin = models.DateField()

    # Financier (Gelé à la signature du bail)
    montant_loyer = models.DecimalField(max_digits=10, decimal_places=0)
    montant_charges = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    depot_garantie = models.DecimalField(max_digits=10, decimal_places=0)
    jour_paiement = models.PositiveIntegerField(default=5, help_text="Jour du mois limite pour payer (ex: le 5)")

    # État du dossier
    est_signe = models.BooleanField(default=False)
    fichier_contrat = models.FileField(upload_to='baux_signes/', blank=True, null=True, help_text="PDF signé")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bail / Contrat"
        verbose_name_plural = "Baux"
        ordering = ['-date_debut']

    def __str__(self):
        return f"Bail {self.locataire.last_name} - {self.bien.titre}"

    def loyer_total(self):
        return self.montant_loyer + self.montant_charges


class Loyer(models.Model):
    """
    Une échéance mensuelle (Facture).
    Généré automatiquement chaque mois.
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

    def __str__(self):
        return f"{self.bail.locataire.username} - {self.periode_debut.strftime('%B %Y')}"

    @property
    def reste_a_payer(self):
        return self.montant_du - self.montant_verse

    @property
    def est_en_retard(self):
        return self.statut != 'PAYE' and date.today() > self.date_echeance
