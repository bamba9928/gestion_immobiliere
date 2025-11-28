from django import forms
from django.utils import timezone
from .models import ContactMessage
from .models import Bien, Bail, Loyer, Annonce, Intervention, EtatDesLieux


# ============================================================================
# BIENS
# ============================================================================

class BienForm(forms.ModelForm):
    class Meta:
        model = Bien
        fields = [
            'titre',
            'type_bien',
            'adresse',
            'ville',
            'surface',
            'nb_pieces',
            'description',
            'loyer_ref',
            'charges_ref',
            'disponible',
            'photo_principale',
        ]
        widgets = {
            'titre': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'placeholder': 'Ex: T3 Centre Ville - Résidence Mada',
            }),
            'type_bien': forms.Select(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
            }),
            'adresse': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'rows': 3,
            }),
            'ville': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'placeholder': 'Dakar',
            }),
            'surface': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'min': 1,
            }),
            'nb_pieces': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'min': 1,
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'rows': 4,
            }),
            'loyer_ref': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'min': 0,
            }),
            'charges_ref': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'min': 0,
            }),
            'disponible': forms.CheckboxInput(attrs={
                'class': 'rounded border-neutral-700',
            }),
            'photo_principale': forms.ClearableFileInput(attrs={
                'class': 'w-full text-sm text-neutral-300',
            }),
        }


# ============================================================================
# BAUX / LOYERS
# ============================================================================

class BailForm(forms.ModelForm):
    class Meta:
        model = Bail
        fields = [
            'bien',
            'locataire',
            'date_debut',
            'date_fin',
            'montant_loyer',
            'montant_charges',
            'depot_garantie',
            'jour_paiement',
            'est_signe',
            'fichier_contrat',
        ]
        widgets = {
            'bien': forms.Select(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
            }),
            'locataire': forms.Select(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
            }),
            'date_debut': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'type': 'date',
            }),
            'date_fin': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'type': 'date',
            }),
            'montant_loyer': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'min': 0,
            }),
            'montant_charges': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'min': 0,
            }),
            'depot_garantie': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'min': 0,
            }),
            'jour_paiement': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'min': 1,
                'max': 28,
            }),
            'est_signe': forms.CheckboxInput(attrs={
                'class': 'rounded border-neutral-700',
            }),
            'fichier_contrat': forms.ClearableFileInput(attrs={
                'class': 'w-full text-sm text-neutral-300',
            }),
        }


class LoyerForm(forms.ModelForm):
    class Meta:
        model = Loyer
        fields = [
            'bail',
            'periode_debut',
            'periode_fin',
            'date_echeance',
            'montant_du',
            'montant_verse',
            'statut',
        ]
        widgets = {
            'bail': forms.Select(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
            }),
            'periode_debut': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'type': 'date',
            }),
            'periode_fin': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'type': 'date',
            }),
            'date_echeance': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'type': 'date',
            }),
            'montant_du': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'min': 0,
            }),
            'montant_verse': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'min': 0,
            }),
            'statut': forms.Select(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
            }),
        }


# ============================================================================
# ANNONCES
# ============================================================================

class AnnonceForm(forms.ModelForm):
    class Meta:
        model = Annonce
        fields = [
            'bien',
            'titre',
            'description',
            'prix',
            'statut',
        ]
        widgets = {
            'bien': forms.Select(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
            }),
            'titre': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'rows': 4,
            }),
            'prix': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'min': 0,
            }),
            'statut': forms.Select(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
            }),
        }


# ============================================================================
# INTERVENTIONS
# ============================================================================

class InterventionForm(forms.ModelForm):
    class Meta:
        model = Intervention
        # bien + locataire + agent sont gérés dans la vue
        fields = [
            'objet',
            'description',
            'photo_avant',
        ]
        widgets = {
            'objet': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'placeholder': "Objet de la demande (plomberie, électricité...)",
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'rows': 4,
                'placeholder': "Décrivez le problème rencontré...",
            }),
            'photo_avant': forms.ClearableFileInput(attrs={
                'class': 'w-full text-sm text-neutral-300',
            }),
        }


# ============================================================================
# ÉTATS DES LIEUX
# ============================================================================

class EtatDesLieuxForm(forms.ModelForm):
    class Meta:
        model = EtatDesLieux
        fields = [
            'bail',
            'type_edl',
            'date_realisation',
            'checklist',
            'commentaire_general',
            'signature_bailleur',
            'signature_locataire',
            'pdf',
        ]
        widgets = {
            'bail': forms.Select(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
            }),
            'type_edl': forms.Select(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
            }),
            'date_realisation': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'type': 'date',
                'value': timezone.now().date().isoformat(),
            }),
            'checklist': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'rows': 6,
            }),
            'commentaire_general': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-white',
                'rows': 4,
            }),
            'signature_bailleur': forms.CheckboxInput(attrs={
                'class': 'rounded border-neutral-700',
            }),
            'signature_locataire': forms.CheckboxInput(attrs={
                'class': 'rounded border-neutral-700',
            }),
            'pdf': forms.ClearableFileInput(attrs={
                'class': 'w-full text-sm text-neutral-300',
            }),
        }

class ContactAnnonceForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["nom", "email", "telephone", "message"]  # adapte aux champs existants
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4}),
        }
class ContactSiteForm(forms.Form):
    nom = forms.CharField(
        label="Nom complet",
        max_length=150,
        widget=forms.TextInput(attrs={
            "placeholder": "Votre nom",
        })
    )

    email = forms.EmailField(
        label="Adresse e-mail",
        widget=forms.EmailInput(attrs={
            "placeholder": "vous@example.com",
        })
    )

    telephone = forms.CharField(
        label="Téléphone",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Optionnel",
        })
    )

    sujet = forms.CharField(
        label="Sujet",
        max_length=200,
        widget=forms.TextInput(attrs={
            "placeholder": "Sujet de votre demande",
        })
    )

    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={
            "rows": 5,
            "placeholder": "Décrivez votre demande…",
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        # Exemple : exiger au moins un moyen de contact
        email = cleaned_data.get("email")
        telephone = cleaned_data.get("telephone")

        if not email and not telephone:
            raise forms.ValidationError(
                "Merci de renseigner au moins un moyen de contact (email ou téléphone)."
            )
        return cleaned_data
