from datetime import date
from decimal import Decimal
import logging
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
from django.views.generic import ListView, DetailView, FormView
from django.urls import reverse_lazy, reverse
from django.views.generic.edit import FormMixin
import weasyprint
from django.conf import settings
from django.core.mail import send_mail

from .forms import (
    BienForm,
    InterventionForm,
    ContactSiteForm,
    ContactAnnonceForm,
    BailForm,
    EtatDesLieuxForm,
)
from .models import (
    Bien,
    Bail,
    Loyer,
    Intervention,
    Annonce,
    EtatDesLieux,
)
from .permissions import (
    is_admin,
    is_bailleur,
    is_locataire,
    is_agent,
    get_active_bail,
)

logger = logging.getLogger(__name__)


# ============================================================================
# PAGES PUBLIQUES (Accès libre)
# ============================================================================
class HomeView(ListView):
    """Page d'accueil publique avec annonces immobilières"""
    model = Annonce
    template_name = 'home.html'
    context_object_name = 'annonces'
    paginate_by = 9

    def get_base_queryset(self):
        """
        Base : annonces publiées dont le bien est disponible
        (est_actif=True + pas de bail actif signé).
        """
        return Annonce.objects.filter(
            statut='PUBLIE',
            bien__in=Bien.objects.disponibles()
        ).select_related('bien', 'bien__proprietaire')

    def get_queryset(self):
        queryset = self.get_base_queryset()

        # Filtre de recherche
        if q := self.request.GET.get('q'):
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

        # Évite un appel supplémentaire à get_queryset()
        queryset = context['annonces']

        context.update({
            'types_bien': Bien.TYPE_CHOICES,
            'villes': (
                Bien.objects.disponibles()
                .filter(annonces__statut='PUBLIE')
                .values_list('ville', flat=True)
                .distinct()
                .order_by('ville')
            ),
            'annonces_count': queryset.count(),
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
        return reverse('annonce_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['annonces_similaires'] = Annonce.objects.filter(
            statut='PUBLIE',
            bien__type_bien=self.object.bien.type_bien,
            bien__ville=self.object.bien.ville
        ).exclude(id=self.object.id)[:3]

        if 'form' not in context:
            context['form'] = self.get_form()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        contact = form.save(commit=False)
        contact.annonce = self.object
        contact.save()
        messages.success(self.request, "Votre message a bien été envoyé. Nous vous recontacterons rapidement.")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, "Veuillez corriger les erreurs dans le formulaire.")
        return self.render_to_response(self.get_context_data(form=form))


class ContactView(FormView):
    """Page de contact générale du site"""
    template_name = "pages/contact.html"
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
        destinataire = getattr(settings, "CONTACT_EMAIL", "admin@votre-site.com")

        try:
            send_mail(
                sujet,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [destinataire],
                fail_silently=False,
            )
            messages.success(self.request, "Votre message a bien été envoyé, nous vous répondrons rapidement.")
        except Exception as e:
            logger.error(f"Erreur envoi email contact: {e}")
            messages.error(self.request, "Une erreur est survenue. Veuillez réessayer plus tard.")

        return super().form_valid(form)


def about(request):
    return render(request, "about.html")


# ============================================================================
# TABLEAU DE BORD & GESTION (Protégé par login)
# ============================================================================

@login_required
def dashboard(request):
    """Tableau de bord multi-rôles centralisé"""
    context = {'user': request.user}

    if is_admin(request.user):
        total_biens = Bien.objects.count()
        biens_occupes = Bien.objects.filter(
            baux__est_signe=True,
            baux__date_debut__lte=date.today(),
            baux__date_fin__gte=date.today(),
        ).distinct().count()

        context.update({
            'user_role': 'ADMIN',
            'total_biens': total_biens,
            'biens_occupes': biens_occupes,
            'taux_occupation': int((biens_occupes / total_biens) * 100) if total_biens > 0 else 0,
            'montant_impayes': Loyer.objects.filter(statut='RETARD').aggregate(
                total=Sum('montant_du')
            )['total'] or 0,
        })

    elif is_bailleur(request.user):
        biens_proprio = Bien.objects.filter(proprietaire=request.user)
        total_biens = biens_proprio.count()
        biens_occupes = biens_proprio.filter(
            baux__est_signe=True,
            baux__date_debut__lte=date.today(),
            baux__date_fin__gte=date.today(),
        ).distinct().count()

        context.update({
            'user_role': 'BAILLEUR',
            'total_biens': total_biens,
            'biens_occupes': biens_occupes,
            'taux_occupation': int((biens_occupes / total_biens) * 100) if total_biens > 0 else 0,
            'montant_impayes': Loyer.objects.filter(
                bail__bien__proprietaire=request.user,
                statut='RETARD',
            ).aggregate(total=Sum('montant_du'))['total'] or 0,
        })

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

    else:
        context['user_role'] = 'AGENT'

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
@login_required
def add_bail(request):
    """
    Création d'un bail depuis le dashboard.
    - Admin : voit tous les biens.
    - Bailleur : ne voit que ses propres biens.
    """
    if not (is_admin(request.user) or is_bailleur(request.user)):
        raise PermissionDenied("Seuls les administrateurs et bailleurs peuvent créer un bail.")

    if request.method == "POST":
        form = BailForm(request.POST, request.FILES)
        # Restreindre le choix des biens pour un bailleur
        if is_bailleur(request.user):
            form.fields["bien"].queryset = Bien.objects.filter(proprietaire=request.user)

        if form.is_valid():
            bail = form.save()
            messages.success(request, "Le bail a été créé avec succès.")
            return redirect("bail_detail", pk=bail.pk)
    else:
        form = BailForm()
        if is_bailleur(request.user):
            form.fields["bien"].queryset = Bien.objects.filter(proprietaire=request.user)

    return render(
        request,
        "baux/add_bail.html",
        {
            "form": form,
            "user_role": "ADMIN" if is_admin(request.user) else "BAILLEUR",
        },
    )
@login_required
def bail_detail(request, pk):
    """
    Fiche détaillée d'un bail :
    - infos bail
    - loyers associés
    - états des lieux (entrée/sortie)
    """
    bail = get_object_or_404(Bail, pk=pk)

    # Permissions : admin, propriétaire du bien ou locataire
    if not (
        is_admin(request.user)
        or bail.bien.proprietaire == request.user
        or bail.locataire == request.user
    ):
        raise PermissionDenied("Vous n'avez pas l'autorisation de consulter ce bail.")

    loyers = bail.loyers.order_by("-date_echeance")  # related_name='loyers' sur Loyer :contentReference[oaicite:7]{index=7}
    etats = bail.etats_des_lieux.order_by("-date_realisation")  # related_name='etats_des_lieux' :contentReference[oaicite:8]{index=8}

    # Pour le template : séparer entrée / sortie si besoin
    edl_entree = etats.filter(type_edl="ENTREE").first()
    edl_sortie = etats.filter(type_edl="SORTIE").first()

    context = {
        "bail": bail,
        "loyers": loyers,
        "etats": etats,
        "edl_entree": edl_entree,
        "edl_sortie": edl_sortie,
        "user_role": (
            "ADMIN"
            if is_admin(request.user)
            else "BAILLEUR"
            if bail.bien.proprietaire == request.user
            else "LOCATAIRE"
        ),
    }
    return render(request, "baux/bail_detail.html", context)
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
        messages.warning(request, "Méthode non autorisée.")
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
    loyer = get_object_or_404(Loyer.objects.select_related('bail__locataire'), id=loyer_id)

    if not is_admin(request.user) and (not loyer.bail or loyer.bail.locataire != request.user):
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
    user_is_admin = is_admin(request.user)
    bail = get_active_bail(request.user) if not user_is_admin else None

    if user_is_admin:
        interventions = Intervention.objects.select_related(
            'bien', 'locataire', 'bien__proprietaire'
        ).all().order_by('-created_at')
    elif bail:
        interventions = Intervention.objects.filter(
            bien=bail.bien,
            locataire=request.user
        ).select_related('bien').order_by('-created_at')
    else:
        return render(request, 'interventions/pas_de_bail.html', {
            'message': "Vous n'avez aucun bail actif."
        })

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

    return render(request, 'interventions/interventions_list.html', {
        'interventions': interventions,
        'form': form,
        'user_role': 'ADMIN' if user_is_admin else 'LOCATAIRE',
        'bail': bail,
    })
@login_required
def add_etat_des_lieux(request, bail_id, type_edl):
    """
    Création d'un EDL d'entrée ou de sortie pour un bail donné.
    type_edl: 'ENTREE' ou 'SORTIE'
    """
    bail = get_object_or_404(Bail, pk=bail_id)

    # Permissions
    if not (
        is_admin(request.user)
        or bail.bien.proprietaire == request.user
        or bail.locataire == request.user
    ):
        raise PermissionDenied("Vous n'avez pas l'autorisation de créer cet état des lieux.")

    if type_edl not in ["ENTREE", "SORTIE"]:
        messages.error(request, "Type d'état des lieux invalide.")
        return redirect("bail_detail", pk=bail.pk)

    if request.method == "POST":
        form = EtatDesLieuxForm(request.POST, request.FILES)
        # On ne laisse pas le user changer le bail/type_edl
        form.fields["bail"].disabled = True
        form.fields["type_edl"].disabled = True

        if form.is_valid():
            edl = form.save(commit=False)
            edl.bail = bail
            edl.type_edl = type_edl
            edl.save()
            messages.success(request, "L'état des lieux a été enregistré avec succès.")
            return redirect("bail_detail", pk=bail.pk)
    else:
        form = EtatDesLieuxForm(
            initial={
                "bail": bail,
                "type_edl": type_edl,
                "date_realisation": timezone.now().date(),
            }
        )
        form.fields["bail"].disabled = True
        form.fields["type_edl"].disabled = True

    return render(
        request,
        "etats_des_lieux/form.html",
        {
            "form": form,
            "bail": bail,
            "type_edl": type_edl,
        },
    )
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
        logger.error(f"Erreur génération loyers: {e}")
        messages.error(request, "Une erreur est survenue. Contactez l'administrateur.")

    return redirect('dashboard')