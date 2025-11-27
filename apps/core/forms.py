from django import forms
from .models import Intervention

class InterventionForm(forms.ModelForm):
    class Meta:
        model = Intervention
        fields = ['objet', 'description', 'photo_avant']
        widgets = {
            'objet': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'Ex: Fuite robinet cuisine'}),
            'description': forms.Textarea(attrs={'class': 'w-full p-2 border rounded', 'rows': 4, 'placeholder': 'Détails du problème...'}),
            'photo_avant': forms.FileInput(attrs={'class': 'w-full p-2'}),
        }