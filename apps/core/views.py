from datetime import date
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.generic import ListView, DetailView
import weasyprint

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, FormView

from .forms import BienForm, InterventionForm, ContactSiteForm


from django.urls import reverse
from django.views.generic import DetailView
from django.views.generic.edit import FormMixin
from django.contrib import messages
from .models import Annonce
from .forms import ContactAnnonceForm


# Models
from .models import Bien, Bail, Loyer, Intervention, Annonce

# Forms
from .forms import BienForm, InterventionForm

# Permissions
from .permissions import (
    is_admin,
    is_bailleur,
    is_locataire,
    is_agent,
    get_active_bail,
)


# ============================================================================
# PAGES PUBLIQUES (Accès libre)
# ============================================================================

class HomeView(ListView):
    """Page d'accueil publique avec annonces immobilières"""
    model = Annonce
    template_name = 'home.html'
    context_object_name = 'annonces'
    paginate_by = 9

    def get_queryset(self):
        queryset = Annonce.objects.filter(
            statut='PUBLIE',
            bien__est_actif=True,
            bien__disponible=True
        ).select_related('bien', 'bien__proprietaire')

        # Filtre de recherche
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(bien__ville__icontains=q) |
                Q(bien__adresse__icontains=q) |
                Q(titre__icontains=q) |
                Q(description__icontains=q)
            )

        # Filtres avancés
        if type_bien := self.request.GET.get('type'):
            queryset = queryset.filter(bien__type_bien=type_bien)

        if ville := self.request.GET.get('ville'):
            queryset = queryset.filter(bien__ville=ville)

        if prix_max := self.request.GET.get('prix_max'):
            queryset = queryset.filter(prix__lte=prix_max)

        # Tri
        sort = self.request.GET.get('sort', '-date_publication')
        return queryset.order_by(sort)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'types_bien': Bien.TYPE_CHOICES,
            'villes': Bien.objects.filter(
                annonces__statut='PUBLIE',
                est_actif=True,
                disponible=True
            ).values_list('ville', flat=True).distinct().order_by('ville'),
            'annonces_count': self.get_queryset().count(),
        })
        return context
class AnnonceDetailView(FormMixin, DetailView):
    """Page de détail d'une annonce publique + formulaire de contact."""
    model = Annonce
    template_name = 'annonce_detail.html'
    context_object_name = 'annonce'
    form_class = ContactAnnonceForm

    def get_queryset(self):
        return Annonce.objects.filter(
            statut='PUBLIE',
            bien__est_actif=True
        ).select_related('bien', 'bien__proprietaire')

    def get_success_url(self):
        # Redirection sur la même page après envoi du formulaire
        return reverse('annonce_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Annonces similaires
        context['annonces_similaires'] = Annonce.objects.filter(
            statut='PUBLIE',
            bien__type_bien=self.object.bien.type_bien,
            bien__ville=self.object.bien.ville
        ).exclude(id=self.object.id)[:3]

        # Formulaire dans le contexte
        if 'form' not in context:
            context['form'] = self.get_form()

        return context

    def post(self, request, *args, **kwargs):
        """Traitement du formulaire de contact."""
        self.object = self.get_object()  # important pour avoir self.object (l'annonce)
        form = self.get_form()

        if form.is_valid():
            contact = form.save(commit=False)
            contact.annonce = self.object
            contact.save()
            messages.success(request, "Votre message a bien été envoyé. Nous vous recontacterons rapidement.")
            return redirect(self.get_success_url())

        # Si formulaire invalide, on réaffiche la page avec les erreurs
        context = self.get_context_data(form=form)
        return self.render_to_response(context)
class ContactView(FormView):
    """Page de contact générale du site"""
    template_name = "pages/contact.html"   # à adapter si ton template a un autre chemin
    form_class = ContactSiteForm
    success_url = reverse_lazy("contact")

    def form_valid(self, form):
        data = form.cleaned_data

        sujet = f"[Contact MADA IMMO] {data.get('sujet')}"
        message = (
            f"Nom : {data.get('nom')}\n"
            f"Email : {data.get('email')}\n"
            f"Téléphone : {data.get('telephone')}\n\n"
            f"Message :\n{data.get('message')}"
        )

        destinataire = getattr(settings, "CONTACT_EMAIL", settings.DEFAULT_FROM_EMAIL)

        send_mail(
            sujet,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [destinataire],
            fail_silently=False,
        )

        messages.success(self.request, "Votre message a bien été envoyé, nous vous répondrons rapidement.")
        return super().form_valid(form)
def about(request):
    return render(request, "about.html")
# ============================================================================
# AUTHENTIFICATION (Utilise les vues Django par défaut)
# ============================================================================
# Les vues login/logout sont directement dans urls.py via auth_views


# ============================================================================
# TABLEAU DE BORD & GESTION (Protégé par login)
# ============================================================================

@login_required
def dashboard(request):
    """Tableau de bord multi-rôles centralisé"""
    context = {'user': request.user}

    # ADMINISTRATEUR
    if is_admin(request.user):
        total_biens = Bien.objects.count()
        biens_occupes = Bien.objects.filter(
            baux__est_signe=True,
            baux__date_fin__gte=date.today(),
        ).distinct().count()

        context.update({
            'user_role': 'ADMIN',
            'total_biens': total_biens,
            'biens_occupes': biens_occupes,
            'taux_occupation': int((biens_occupes / total_biens) * 100) if total_biens else 0,
            'montant_impayes': Loyer.objects.filter(statut='RETARD').aggregate(
                total=Sum('montant_du')
            )['total'] or 0,
        })

    # BAILLEUR
    elif is_bailleur(request.user):
        biens_proprio = Bien.objects.filter(proprietaire=request.user)
        total_biens = biens_proprio.count()
        biens_occupes = biens_proprio.filter(
            baux__est_signe=True,
            baux__date_fin__gte=date.today(),
        ).distinct().count()

        context.update({
            'user_role': 'BAILLEUR',
            'total_biens': total_biens,
            'biens_occupes': biens_occupes,
            'taux_occupation': int((biens_occupes / total_biens) * 100) if total_biens else 0,
            'montant_impayes': Loyer.objects.filter(
                bail__bien__proprietaire=request.user,
                statut='RETARD',
            ).aggregate(total=Sum('montant_du'))['total'] or 0,
        })

    # LOCATAIRE
    elif is_locataire(request.user):
        bail = get_active_bail(request.user)
        context.update({
            'user_role': 'LOCATAIRE',
            'bail': bail,
        })
        if bail:
            context['dernier_loyer'] = Loyer.objects.filter(bail=bail).order_by(
                '-date_echeance'
            ).first()

    # AGENT ou AUTRE
    else:
        context['user_role'] = 'AGENT' if is_agent(request.user) else 'VISITEUR'

    return render(request, 'dashboard.html', context)


# ============================================================================
# GESTION DES BIENS
# ============================================================================

@login_required
def add_bien(request):
    """Ajout d'un bien (Admin ou Propriétaire)"""
    if not (is_admin(request.user) or is_bailleur(request.user)):
        raise PermissionDenied("Seuls les administrateurs et propriétaires peuvent ajouter des biens.")

    if request.method == 'POST':
        form = BienForm(request.POST, request.FILES)
        if form.is_valid():
            bien = form.save(commit=False)
            bien.proprietaire = request.user
            bien.save()
            messages.success(request, f"Le bien '{bien.titre}' a été ajouté avec succès !")
            return redirect('dashboard')
    else:
        form = BienForm()

    return render(request, 'biens/add_bien.html', {
        'form': form,
        'user_role': 'ADMIN' if is_admin(request.user) else 'PROPRIÉTAIRE'
    })


# ============================================================================
# GESTION DES LOYERS
# ============================================================================

@login_required
def loyers_list(request):
    """Gestion des loyers (Admin uniquement)"""
    if not is_admin(request.user):
        raise PermissionDenied("Accès réservé aux administrateurs.")

    statut = request.GET.get('statut')
    loyers = Loyer.objects.select_related('bail__locataire', 'bail__bien').order_by('-date_echeance')

    if statut:
        loyers = loyers.filter(statut=statut)

    stats = {
        'total_retard': loyers.filter(statut='RETARD').count(),
        'total_attente': loyers.filter(statut='A_PAYER').count(),
    }

    return render(request, 'interventions/loyers_list.html', {
        'loyers': loyers,
        'current_statut': statut,
        'stats': stats,
    })


@login_required
def mark_loyer_paid(request, loyer_id):
    """Marquer un loyer comme payé (Admin uniquement)"""
    if not is_admin(request.user):
        raise PermissionDenied("Accès réservé aux administrateurs.")

    if request.method != 'POST':
        return redirect('loyers_list')

    loyer = get_object_or_404(Loyer, id=loyer_id)
    loyer.statut = 'PAYE'
    loyer.montant_verse = loyer.montant_du
    loyer.date_paiement = timezone.now()
    loyer.save()
    messages.success(request, f"Loyer de {loyer.bail.locataire} marqué comme payé.")
    return redirect('loyers_list')


@login_required
def download_quittance(request, loyer_id):
    """Téléchargement de quittance PDF (Admin ou Locataire concerné)"""
    loyer = get_object_or_404(Loyer, id=loyer_id)

    # Sécurité : admin ou locataire concerné
    if not is_admin(request.user) and loyer.bail.locataire != request.user:
        raise PermissionDenied("Accès non autorisé à cette quittance.")

    if loyer.statut != 'PAYE':
        messages.error(request, "La quittance n'est disponible que pour les loyers payés.")
        return redirect('dashboard')

    html_string = render_to_string('documents/quittance.html', {
        'loyer': loyer,
        'now': timezone.now(),
    })

    response = HttpResponse(content_type='application/pdf')
    filename = f"Quittance_{loyer.periode_debut.strftime('%Y-%m')}_{loyer.bail.locataire.username}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    weasyprint.HTML(string=html_string).write_pdf(response)

    return response


# ============================================================================
# GESTION DES INTERVENTIONS
# ============================================================================

@login_required
def interventions_list(request):
    """Gestion des interventions (Admin ou Locataire avec bail actif)"""
    bail = get_active_bail(request.user) if not is_admin(request.user) else None

    # Admin voit tout
    if is_admin(request.user):
        interventions = Intervention.objects.all().order_by('-created_at')
    # Locataire avec bail voit ses interventions
    elif bail:
        interventions = Intervention.objects.filter(
            bien=bail.bien,
            locataire=request.user
        ).order_by('-created_at')
    else:
        return render(request, 'interventions/pas_de_bail.html', {
            'message': "Vous n'avez aucun bail actif."
        })

    # Gestion du formulaire pour locataires
    form = InterventionForm()
    if request.method == 'POST':
        if not bail:
            messages.error(request, "Impossible de créer une intervention sans bail actif.")
            return redirect('interventions_list')

        form = InterventionForm(request.POST, request.FILES)
        if form.is_valid():
            intervention = form.save(commit=False)
            intervention.locataire = request.user
            intervention.bien = bail.bien
            intervention.save()
            messages.success(request, "Demande d'intervention enregistrée avec succès.")
            return redirect('interventions_list')

    return render(request, 'interventions/loyers_list.html', {
        'interventions': interventions,
        'form': form,
        'user_role': 'ADMIN' if is_admin(request.user) else 'LOCATAIRE',
        'bail': bail,
    })


# ============================================================================
# ACTIONS ADMINISTRATIVES
# ============================================================================

@login_required
def trigger_rent_generation(request):
    """Lancement manuel de la génération des loyers (Admin uniquement)"""
    if not is_admin(request.user):
        raise PermissionDenied("Seul un administrateur peut générer les loyers.")

    if request.method != 'POST':
        messages.warning(request, "Méthode non autorisée. Utilisez le bouton du tableau de bord.")
        return redirect('dashboard')

    try:
        call_command('generer_loyers')
        messages.success(request, "✅ Génération des loyers effectuée avec succès.")
    except Exception as e:
        messages.error(request, f"❌ Erreur lors de la génération : {str(e)}")

    return redirect('dashboard')
