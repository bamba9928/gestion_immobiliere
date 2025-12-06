from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


# ================== QUERYSET PERSONNALISÉ ==================

class BienQuerySet(models.QuerySet):
    """Manager personnalisé avec méthodes métier."""

    def disponibles(self):
        """Retourne les biens disponibles à la location."""
        aujourd_hui = date.today()
        return (
            self.filter(est_actif=True)
            .exclude(
                baux__est_signe=True,
                baux__date_debut__lte=aujourd_hui,
                baux__date_fin__gte=aujourd_hui,
            )
            .distinct()
        )

    def occupes(self):
        """Retourne les biens actuellement loués."""
        aujourd_hui = date.today()
        return (
            self.filter(
                est_actif=True,
                baux__est_signe=True,
                baux__date_debut__lte=aujourd_hui,
                baux__date_fin__gte=aujourd_hui,
            )
            .distinct()
        )


# ===================== MODEL BIEN =====================

class Bien(models.Model):
    TYPE_CHOICES = [
        ("APPARTEMENT", "Appartement"),
        ("MAISON", "Maison"),
        ("COMMERCE", "Local Commercial"),
        ("TERRAIN", "Terrain"),
    ]

    # Infos principales
    titre = models.CharField(
        max_length=200,
        help_text="Ex: T3 Centre Ville - Résidence Mada",
    )
    type_bien = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="APPARTEMENT",
    )
    adresse = models.TextField()
    ville = models.CharField(max_length=100, default="Dakar")

    # Caractéristiques
    surface = models.PositiveIntegerField(help_text="En m²")
    nb_pieces = models.PositiveIntegerField(
        verbose_name="Nombre de pièces",
        default=1,
    )
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

    # Gestion
    proprietaire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="biens_possedes",
    )
    photo_principale = models.ImageField(
        upload_to="biens/",
        blank=True,
        null=True,
    )
    est_actif = models.BooleanField(
        default=True,
        help_text="Décochez si le bien est vendu ou retiré de la gestion",
    )

    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Manager personnalisé
    objects = BienQuerySet.as_manager()

    class Meta:
        verbose_name = "Bien Immobilier"
        verbose_name_plural = "Biens Immobiliers"
        indexes = [
            models.Index(fields=["est_actif", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_type_bien_display()} - {self.titre}"

    @property
    def est_occupe(self) -> bool:
        """Vérifie si un bail actif et signé existe."""
        aujourd_hui = date.today()
        return self.baux.filter(
            est_signe=True,
            date_debut__lte=aujourd_hui,
            date_fin__gte=aujourd_hui,
        ).exists()

    @property
    def est_disponible(self) -> bool:
        """
        Un bien est disponible si :
        - Il est marqué actif (non vendu/retiré)
        - Aucun bail actif signé n'existe
        """
        return self.est_actif and not self.est_occupe

    @property
    def bail_actif(self):
        """Retourne le bail en cours s'il existe."""
        aujourd_hui = date.today()
        return self.baux.filter(
            est_signe=True,
            date_debut__lte=aujourd_hui,
            date_fin__gte=aujourd_hui,
        ).first()


# ===================== MODEL BAIL =====================

class Bail(models.Model):
    """Contrat de location liant un bien et un locataire."""

    bien = models.ForeignKey(
        Bien,
        on_delete=models.PROTECT,
        related_name="baux",
    )
    locataire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="baux",
    )

    # Dates clés
    date_debut = models.DateField()
    date_fin = models.DateField()

    # Financier (gelé à la signature)
    montant_loyer = models.DecimalField(max_digits=10, decimal_places=0)
    montant_charges = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
    )
    depot_garantie = models.DecimalField(max_digits=10, decimal_places=0)
    jour_paiement = models.PositiveIntegerField(
        default=5,
        help_text="Jour du mois limite pour payer (ex: le 5)",
    )

    # État du dossier
    est_signe = models.BooleanField(default=False)
    fichier_contrat = models.FileField(
        upload_to="baux_signes/",
        blank=True,
        null=True,
        help_text="PDF signé",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bail / Contrat"
        verbose_name_plural = "Baux"
        ordering = ["-date_debut"]
        indexes = [
            models.Index(fields=["bien", "est_signe", "date_fin"]),
        ]

    def __str__(self) -> str:
        return f"Bail {self.locataire.last_name} - {self.bien.titre}"

    def loyer_total(self) -> int:
        """Retourne le loyer mensuel charges comprises."""
        return int(self.montant_loyer + self.montant_charges)

    def clean(self):
        """Validation métier avant enregistrement."""
        from django.core.exceptions import ValidationError

        # Vérifier cohérence des dates
        if self.date_fin <= self.date_debut:
            raise ValidationError("La date de fin doit être postérieure à la date de début.")

        # Empêcher la création de baux qui se chevauchent (si signé)
        if self.est_signe:
            chevauchements = Bail.objects.filter(
                bien=self.bien,
                est_signe=True,
                date_debut__lte=self.date_fin,
                date_fin__gte=self.date_debut,
            ).exclude(pk=self.pk)

            if chevauchements.exists():
                raise ValidationError(
                    f"Ce bien a déjà un bail actif pour cette période. "
                    f"Bail existant : {chevauchements.first()}"
                )

    def save(self, *args, **kwargs):
        """
        Aucune logique de mise à jour de disponibilité.
        La propriété calculée sur Bien gère tout automatiquement.
        """
        self.full_clean()
        super().save(*args, **kwargs)


# ===================== MODEL LOYER =====================

class Loyer(models.Model):
    STATUT_CHOICES = [
        ("A_PAYER", "À payer"),
        ("PARTIEL", "Paiement partiel"),
        ("PAYE", "Payé"),
        ("RETARD", "En retard"),
    ]

    bail = models.ForeignKey(
        Bail,
        on_delete=models.PROTECT,
        related_name="loyers",
    )
    periode_debut = models.DateField()
    periode_fin = models.DateField()
    date_echeance = models.DateField(help_text="Date limite de paiement")
    montant_du = models.DecimalField(max_digits=10, decimal_places=0)
    montant_verse = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
    )
    statut = models.CharField(
        max_length=10,
        choices=STATUT_CHOICES,
        default="A_PAYER",
    )
    date_paiement = models.DateTimeField(null=True, blank=True)
    quittance = models.FileField(
        upload_to="quittances/",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Loyer / Échéance"
        verbose_name_plural = "Loyers"
        unique_together = ("bail", "periode_debut")

    def __str__(self) -> str:
        return f"{self.bail.locataire.username} - {self.periode_debut.strftime('%B %Y')}"

    @property
    def reste_a_payer(self) -> int:
        return int(self.montant_du - self.montant_verse)

    @property
    def est_en_retard(self) -> bool:
        return self.statut != "PAYE" and date.today() > self.date_echeance

    def enregistrer_paiement(self, montant: Decimal) -> None:
        if montant <= 0:
            raise ValueError("Le montant du paiement doit être positif.")

        nouveau_total = self.montant_verse + Decimal(montant)
        self.montant_verse = min(nouveau_total, self.montant_du)

        if self.montant_verse >= self.montant_du:
            self.statut = "PAYE"
            self.date_paiement = timezone.now()
            self.montant_verse = self.montant_du
        else:
            self.statut = "PARTIEL"
            self.date_paiement = None

        self.save(update_fields=["montant_verse", "statut", "date_paiement"])
        if self.statut == "PAYE":
            from apps.core.services.quittance import attacher_quittance

            attacher_quittance(self)

    def actualiser_statut_retard(self) -> None:
        if self.statut == "PAYE":
            return
        if date.today() > self.date_echeance:
            self.statut = "RETARD"
            self.save(update_fields=["statut"])


# ===================== MODEL ANNONCE =====================

class Annonce(models.Model):
    STATUT_CHOICES = [
        ("BROUILLON", "Brouillon"),
        ("ATTENTE", "En attente"),
        ("PUBLIE", "Publiée"),
        ("ARCHIVE", "Archivée"),
    ]

    bien = models.ForeignKey(
        Bien,
        on_delete=models.PROTECT,
        related_name="annonces",
    )
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    prix = models.DecimalField(max_digits=10, decimal_places=0)
    statut = models.CharField(
        max_length=10,
        choices=STATUT_CHOICES,
        default="BROUILLON",
    )
    date_publication = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Annonce"
        verbose_name_plural = "Annonces"
        ordering = ["-date_publication"]

    def __str__(self) -> str:
        return f"{self.bien} - {self.get_statut_display()}"

    @property
    def est_recente(self) -> bool:
        """
        Indique si l'annonce a été publiée il y a moins de 7 jours.
        Utilisé pour afficher le badge "Nouveau" sur la page d'accueil.
        """
        if not self.date_publication:
            return False

        limite = timezone.now() - timedelta(days=7)
        return self.date_publication >= limite


# ===================== MODEL INTERVENTION =====================

class Intervention(models.Model):
    STATUT_CHOICES = [
        ("NOUVEAU", "Nouveau"),
        ("EN_COURS", "En cours"),
        ("RESOLU", "Résolu"),
    ]

    bien = models.ForeignKey(
        Bien,
        on_delete=models.PROTECT,
        related_name="interventions",
    )
    locataire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="interventions",
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="interventions_assignees",
        null=True,
        blank=True,
    )
    objet = models.CharField(max_length=200)
    description = models.TextField()
    statut = models.CharField(
        max_length=10,
        choices=STATUT_CHOICES,
        default="NOUVEAU",
    )
    photo_avant = models.ImageField(
        upload_to="interventions/avant/",
        null=True,
        blank=True,
    )
    photo_apres = models.ImageField(
        upload_to="interventions/apres/",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Intervention"
        verbose_name_plural = "Interventions"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.objet} - {self.get_statut_display()}"


# ===================== MODEL ÉTAT DES LIEUX =====================

class EtatDesLieux(models.Model):
    TYPE_CHOICES = [
        ("ENTREE", "Entrée"),
        ("SORTIE", "Sortie"),
    ]

    bail = models.ForeignKey(
        Bail,
        on_delete=models.CASCADE,
        related_name="etats_des_lieux",
    )
    type_edl = models.CharField(max_length=10, choices=TYPE_CHOICES)
    date_realisation = models.DateField(default=timezone.localdate)
    checklist = models.TextField(
        blank=True,
        help_text="Checklist ou notes détaillées de l'état des lieux.",
    )
    commentaire_general = models.TextField(blank=True)
    signature_bailleur = models.BooleanField(default=False)
    signature_locataire = models.BooleanField(default=False)
    pdf = models.FileField(
        upload_to="edl/",
        blank=True,
        null=True,
        help_text="PDF de l'état des lieux signé.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "État des lieux"
        verbose_name_plural = "États des lieux"
        ordering = ["-date_realisation"]

    def __str__(self):
        return f"EDL {self.get_type_edl_display()} - {self.bail_id}"


# ===================== MODEL CONTACT =====================

class ContactMessage(models.Model):
    nom = models.CharField(max_length=150)
    email = models.EmailField()
    telephone = models.CharField(max_length=30, blank=True)
    message = models.TextField()
    annonce = models.ForeignKey(
        Annonce,
        on_delete=models.CASCADE,
        related_name="messages",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.nom} - {self.created_at:%Y-%m-%d}"


# ===================== MODEL TRANSACTION =====================

class Transaction(models.Model):
    PROVIDERS = [
        ("WAVE", "Wave"),
        ("OM", "Orange Money"),
        ("CASH", "Espèces"),
    ]
    TYPE_FLUX = [
        ("LOYER", "Paiement Loyer"),
        ("DEPOT", "Dépôt de garantie"),
        ("REGUL", "Régularisation Charges"),
    ]

    loyer = models.ForeignKey(
        Loyer,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    montant = models.DecimalField(max_digits=10, decimal_places=0)
    provider = models.CharField(max_length=10, choices=PROVIDERS)
    reference_externe = models.CharField(
        max_length=100,
        blank=True,
        help_text="ID de transaction fourni par l'opérateur (ex: Wave ID)",
    )
    type_flux = models.CharField(
        max_length=10,
        choices=TYPE_FLUX,
        default="LOYER",
    )
    preuve_paiement = models.FileField(
        upload_to="preuves/",
        null=True,
        blank=True,
    )
    est_validee = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    def __str__(self):
        return f"{self.provider} - {self.montant} FCFA ({self.get_statut_display()})"

    def get_statut_display(self):
        return "Validée" if self.est_validee else "En attente"


# ===================== MODEL DÉPENSE =====================

class Depense(models.Model):
    TYPE_DEPENSE = [
        ("REPARATION", "Réparation / Entretien"),
        ("EAU_ELEC", "Eau / Électricité (Parties communes)"),
        ("TAXE", "Taxe Foncière / TOM"),
        ("ASSURANCE", "Assurance PNO"),
        ("SYNDIC", "Charges de copropriété"),
        ("AUTRE", "Autre"),
    ]

    bien = models.ForeignKey(
        Bien,
        on_delete=models.CASCADE,
        related_name="depenses",
        verbose_name="Bien concerné",
    )
    # Optionnel : lier à un bail spécifique si la dépense est imputable à un locataire
    bail = models.ForeignKey(
        Bail,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="depenses_imputables",
    )

    type_depense = models.CharField(max_length=20, choices=TYPE_DEPENSE)
    libelle = models.CharField(
        max_length=200,
        help_text="Ex: Remplacement robinet cuisine",
    )
    montant = models.DecimalField(max_digits=10, decimal_places=0)
    date_paiement = models.DateField(default=timezone.localdate)

    est_recuperable = models.BooleanField(
        default=False,
        help_text="Cochez si cette dépense est refacturable au locataire (charges récupérables)",
    )

    justificatif = models.FileField(
        upload_to="depenses/justificatifs/",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"
        ordering = ["-date_paiement"]

    def __str__(self):
        return f"{self.libelle} - {self.montant} FCFA"
# ===================== MODEL HISTORIQUE RELANCE =====================

class HistoriqueRelance(models.Model):
    CANAL_CHOICES = [
        ("EMAIL", "Email"),
        ("SMS", "SMS"),
        ("AUTRE", "Autre"),
    ]

    loyer = models.ForeignKey(
        Loyer,
        on_delete=models.CASCADE,
        related_name="relances",
    )
    date_envoi = models.DateTimeField(auto_now_add=True)
    canal = models.CharField(
        max_length=10,
        choices=CANAL_CHOICES,
        default="EMAIL",
    )
    succes = models.BooleanField(default=True)
    message = models.TextField(blank=True)

    class Meta:
        verbose_name = "Relance de paiement"
        verbose_name_plural = "Relances de paiement"
        ordering = ["-date_envoi"]

    def __str__(self):
        return f"Relance {self.canal} pour loyer {self.loyer_id} ({self.date_envoi:%Y-%m-%d %H:%M})"
