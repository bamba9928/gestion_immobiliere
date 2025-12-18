from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q


from .models import (
ContactMessage,
    Bien,
    Bail,
    Loyer,
    Annonce,
    Intervention,
    EtatDesLieux,
    Depense,
)
User = get_user_model()
# ============================================================================
# STYLES COMMUNS (TAILWIND PREMIUM DARK)
# ============================================================================
STYLE_INPUT = "w-full px-4 py-3 rounded-xl bg-neutral-900 border border-neutral-800 text-white placeholder-neutral-600 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-all"
STYLE_CHECKBOX = "w-5 h-5 rounded border-neutral-700 bg-neutral-900 text-emerald-500 focus:ring-emerald-500"
STYLE_FILE = "w-full text-sm text-neutral-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-neutral-800 file:text-emerald-500 hover:file:bg-neutral-700 cursor-pointer"


# ============================================================================
# BIENS
# ============================================================================

class BienForm(forms.ModelForm):
    class Meta:
        model = Bien
        fields = [
            'titre', 'type_bien', 'adresse', 'ville', 'surface',
            'nb_pieces', 'description', 'loyer_ref', 'charges_ref', 'photo_principale'
        ]
        widgets = {
            'titre': forms.TextInput(attrs={'class': STYLE_INPUT, 'placeholder': 'Ex: T3 Centre Ville'}),
            'type_bien': forms.Select(attrs={'class': STYLE_INPUT}),
            'adresse': forms.Textarea(attrs={'class': STYLE_INPUT, 'rows': 2}),
            'ville': forms.TextInput(attrs={'class': STYLE_INPUT, 'placeholder': 'Dakar'}),
            'surface': forms.NumberInput(attrs={'class': STYLE_INPUT, 'min': 1}),
            'nb_pieces': forms.NumberInput(attrs={'class': STYLE_INPUT, 'min': 1}),
            'description': forms.Textarea(attrs={'class': STYLE_INPUT, 'rows': 4}),
            'loyer_ref': forms.NumberInput(attrs={'class': STYLE_INPUT, 'min': 0}),
            'charges_ref': forms.NumberInput(attrs={'class': STYLE_INPUT, 'min': 0}),
            'photo_principale': forms.ClearableFileInput(attrs={'class': STYLE_FILE}),
        }


# ============================================================================
# BAUX / LOYERS
# ============================================================================

class BailForm(forms.ModelForm):
    class Meta:
        model = Bail
        fields = [
            'bien', 'locataire', 'date_debut', 'date_fin',
            'montant_loyer', 'montant_charges', 'depot_garantie',
            'jour_paiement', 'est_signe', 'fichier_contrat'
        ]
        widgets = {
            'bien': forms.Select(attrs={'class': STYLE_INPUT}),
            'locataire': forms.Select(attrs={'class': STYLE_INPUT}),
            'date_debut': forms.DateInput(attrs={'class': STYLE_INPUT, 'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'class': STYLE_INPUT, 'type': 'date'}),
            'montant_loyer': forms.NumberInput(attrs={'class': STYLE_INPUT}),
            'montant_charges': forms.NumberInput(attrs={'class': STYLE_INPUT}),
            'depot_garantie': forms.NumberInput(attrs={'class': STYLE_INPUT}),
            'jour_paiement': forms.NumberInput(attrs={'class': STYLE_INPUT, 'min': 1, 'max': 31}),
            'est_signe': forms.CheckboxInput(attrs={'class': STYLE_CHECKBOX}),
            'fichier_contrat': forms.ClearableFileInput(attrs={'class': STYLE_FILE}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # CORRECTION ICI : On utilise User (qui est maintenant get_user_model())
        self.fields['locataire'].queryset = User.objects.filter(
            groups__name='LOCATAIRE'
        ).order_by('last_name')

        # Affichage propre "Nom Prénom (email)"
        self.fields['locataire'].label_from_instance = lambda obj: f"{obj.get_full_name()} ({obj.email})"


class LoyerForm(forms.ModelForm):
    class Meta:
        model = Loyer
        fields = [
            'bail', 'periode_debut', 'periode_fin', 'date_echeance',
            'montant_du', 'montant_verse', 'statut'
        ]
        widgets = {
            'bail': forms.Select(attrs={'class': STYLE_INPUT}),
            'periode_debut': forms.DateInput(attrs={'class': STYLE_INPUT, 'type': 'date'}),
            'periode_fin': forms.DateInput(attrs={'class': STYLE_INPUT, 'type': 'date'}),
            'date_echeance': forms.DateInput(attrs={'class': STYLE_INPUT, 'type': 'date'}),
            'montant_du': forms.NumberInput(attrs={'class': STYLE_INPUT}),
            'montant_verse': forms.NumberInput(attrs={'class': STYLE_INPUT}),
            'statut': forms.Select(attrs={'class': STYLE_INPUT}),
        }


# ============================================================================
# ANNONCES
# ============================================================================

class AnnonceForm(forms.ModelForm):
    class Meta:
        model = Annonce
        fields = ['bien', 'titre', 'description', 'prix', 'statut']
        widgets = {
            'bien': forms.Select(attrs={'class': STYLE_INPUT}),
            'titre': forms.TextInput(attrs={'class': STYLE_INPUT}),
            'description': forms.Textarea(attrs={'class': STYLE_INPUT, 'rows': 4}),
            'prix': forms.NumberInput(attrs={'class': STYLE_INPUT}),
            'statut': forms.Select(attrs={'class': STYLE_INPUT}),
        }


# ============================================================================
# INTERVENTIONS
# ============================================================================

class InterventionForm(forms.ModelForm):
    class Meta:
        model = Intervention
        fields = ['objet', 'description', 'photo_avant']
        widgets = {
            'objet': forms.TextInput(attrs={'class': STYLE_INPUT, 'placeholder': "Ex: Fuite d'eau..."}),
            'description': forms.Textarea(attrs={'class': STYLE_INPUT, 'rows': 4, 'placeholder': "Détails..."}),
            'photo_avant': forms.ClearableFileInput(attrs={'class': STYLE_FILE}),
        }


# ============================================================================
# ÉTATS DES LIEUX
# ============================================================================

class EtatDesLieuxForm(forms.ModelForm):
    class Meta:
        model = EtatDesLieux
        fields = [
            'bail', 'type_edl', 'date_realisation', 'checklist',
            'commentaire_general', 'signature_bailleur', 'signature_locataire', 'pdf'
        ]
        widgets = {
            'bail': forms.Select(attrs={'class': STYLE_INPUT}),
            'type_edl': forms.Select(attrs={'class': STYLE_INPUT}),
            'date_realisation': forms.DateInput(attrs={'class': STYLE_INPUT, 'type': 'date'}),
            'checklist': forms.Textarea(attrs={'class': STYLE_INPUT, 'rows': 6}),
            'commentaire_general': forms.Textarea(attrs={'class': STYLE_INPUT, 'rows': 4}),
            'signature_bailleur': forms.CheckboxInput(attrs={'class': STYLE_CHECKBOX}),
            'signature_locataire': forms.CheckboxInput(attrs={'class': STYLE_CHECKBOX}),
            'pdf': forms.ClearableFileInput(attrs={'class': STYLE_FILE}),
        }


# ============================================================================
# CONTACT & UTILISATEURS
# ============================================================================

class ContactAnnonceForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["nom", "email", "telephone", "message"]
        widgets = {
            'nom': forms.TextInput(attrs={'class': STYLE_INPUT}),
            'email': forms.EmailInput(attrs={'class': STYLE_INPUT}),
            'telephone': forms.TextInput(attrs={'class': STYLE_INPUT}),
            'message': forms.Textarea(attrs={'class': STYLE_INPUT, 'rows': 4}),
        }


class ContactSiteForm(forms.Form):
    nom = forms.CharField(
        label="Nom complet",
        max_length=150,
        widget=forms.TextInput(attrs={'class': STYLE_INPUT, 'placeholder': "Votre nom"})
    )
    email = forms.EmailField(
        label="Adresse e-mail",
        widget=forms.EmailInput(attrs={'class': STYLE_INPUT, 'placeholder': "vous@example.com"})
    )
    telephone = forms.CharField(
        label="Téléphone",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': STYLE_INPUT, 'placeholder': "Optionnel"})
    )
    sujet = forms.CharField(
        label="Sujet",
        max_length=200,
        widget=forms.TextInput(attrs={'class': STYLE_INPUT, 'placeholder': "Sujet de votre demande"})
    )
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={'class': STYLE_INPUT, 'rows': 5, 'placeholder': "Décrivez votre demande…"})
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        telephone = cleaned_data.get("telephone")
        if not email and not telephone:
            raise forms.ValidationError("Merci de renseigner au moins un moyen de contact.")
        return cleaned_data
class LocataireCreationForm(UserCreationForm):
    """Formulaire spécifique pour la création de locataire avec infos étendues"""

    telephone = forms.CharField(
        label="Téléphone",
        required=True,
        widget=forms.TextInput(attrs={'class': STYLE_INPUT, 'placeholder': '+221...'})
    )
    cni_numero = forms.CharField(
        label="Numéro CNI / Passeport",
        required=True,
        widget=forms.TextInput(attrs={'class': STYLE_INPUT})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
        )
        widgets = {
            "username": forms.TextInput(attrs={"class": STYLE_INPUT}),
            "first_name": forms.TextInput(attrs={"class": STYLE_INPUT}),
            "last_name": forms.TextInput(attrs={"class": STYLE_INPUT}),
            "email": forms.EmailInput(attrs={"class": STYLE_INPUT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Appliquer le style Tailwind aux champs de mot de passe
        self.fields["password1"].widget.attrs.setdefault("class", STYLE_INPUT)
        self.fields["password2"].widget.attrs.setdefault("class", STYLE_INPUT)

    def save(self, commit=True):
        user = super().save(commit=False)  # gère déjà password1/password2 + hash
        if commit:
            user.save()

            if hasattr(user, "profile"):
                user.profile.telephone = self.cleaned_data["telephone"]
                user.profile.cni_numero = self.cleaned_data["cni_numero"]
                user.profile.save()
        return user
class DepenseForm(forms.ModelForm):
    class Meta:
        model = Depense
        fields = ['bien', 'type_depense', 'libelle', 'montant', 'date_paiement', 'est_recuperable', 'justificatif']
        widgets = {
            'bien': forms.Select(attrs={'class': STYLE_INPUT}),
            'type_depense': forms.Select(attrs={'class': STYLE_INPUT}),
            'libelle': forms.TextInput(attrs={'class': STYLE_INPUT}),
            'montant': forms.NumberInput(attrs={'class': STYLE_INPUT}),
            'date_paiement': forms.DateInput(attrs={'class': STYLE_INPUT, 'type': 'date'}),
            'est_recuperable': forms.CheckboxInput(attrs={'class': STYLE_CHECKBOX}),
            'justificatif': forms.ClearableFileInput(attrs={'class': STYLE_FILE}),
        }
class UnifiedCreationForm(forms.Form):
    # LOCATAIRE (profil)
    first_name = forms.CharField(label="Prénom", max_length=150, widget=forms.TextInput(attrs={"class": STYLE_INPUT}))
    last_name = forms.CharField(label="Nom", max_length=150, widget=forms.TextInput(attrs={"class": STYLE_INPUT}))
    email = forms.EmailField(label="Email / Identifiant", widget=forms.EmailInput(attrs={"class": STYLE_INPUT}))
    telephone = forms.CharField(label="Téléphone", max_length=30, widget=forms.TextInput(attrs={"class": STYLE_INPUT}))
    cni_numero = forms.CharField(label="Numéro CNI / Passeport", max_length=60, widget=forms.TextInput(attrs={"class": STYLE_INPUT}))

    # BIEN
    titre_bien = forms.CharField(label="Nom du Bien", widget=forms.TextInput(attrs={"class": STYLE_INPUT}))
    type_bien = forms.ChoiceField(choices=Bien.TYPE_CHOICES, label="Type de bien", widget=forms.Select(attrs={"class": STYLE_INPUT}))
    adresse = forms.CharField(label="Adresse précise", widget=forms.Textarea(attrs={"class": STYLE_INPUT, "rows": 2}))
    ville = forms.CharField(label="Ville", max_length=100, initial="Dakar", widget=forms.TextInput(attrs={"class": STYLE_INPUT}))
    surface = forms.IntegerField(label="Surface (m²)", widget=forms.NumberInput(attrs={"class": STYLE_INPUT, "min": 1}))
    nb_pieces = forms.IntegerField(label="Nombre de pièces", required=False, widget=forms.NumberInput(attrs={"class": STYLE_INPUT, "min": 1}))

    # BAIL
    date_debut = forms.DateField(label="Début du bail", widget=forms.DateInput(attrs={"class": STYLE_INPUT, "type": "date"}))
    date_fin = forms.DateField(label="Fin du bail", widget=forms.DateInput(attrs={"class": STYLE_INPUT, "type": "date"}))  # obligatoire (model)
    montant_loyer = forms.DecimalField(max_digits=10, decimal_places=0, label="Loyer mensuel", widget=forms.NumberInput(attrs={"class": STYLE_INPUT, "min": 0}))
    montant_charges = forms.DecimalField(max_digits=10, decimal_places=0, label="Charges", initial=0, required=False, widget=forms.NumberInput(attrs={"class": STYLE_INPUT, "min": 0}))
    depot_garantie = forms.DecimalField(max_digits=10, decimal_places=0, label="Dépôt de garantie", widget=forms.NumberInput(attrs={"class": STYLE_INPUT, "min": 0}))
    jour_paiement = forms.IntegerField(label="Jour limite de paiement", initial=5, required=False, widget=forms.NumberInput(attrs={"class": STYLE_INPUT, "min": 1, "max": 31}))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_user = user

        # ADMIN : choisir le propriétaire du bien (bailleur)
        if user and getattr(user, "groups", None) and user.groups.filter(name="ADMIN").exists():
            qs = User.objects.filter(
                Q(groups__name="BAILLEUR") | Q(id=user.id)  # bailleurs + admin lui-même si besoin
            ).distinct().order_by("last_name", "first_name")

            self.fields["proprietaire"] = forms.ModelChoiceField(
                label="Propriétaire (Bailleur)",
                queryset=qs,
                widget=forms.Select(attrs={"class": STYLE_INPUT}),
                required=True,
            )
            self.fields["proprietaire"].label_from_instance = lambda u: f"{u.get_full_name() or u.username} ({u.email})"

    def clean_email(self):
        return (self.cleaned_data["email"] or "").strip().lower()

    def clean(self):
        cleaned = super().clean()
        d1, d2 = cleaned.get("date_debut"), cleaned.get("date_fin")
        if d1 and d2 and d2 <= d1:
            raise forms.ValidationError("La date de fin doit être postérieure à la date de début.")
        return cleaned
