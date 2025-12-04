import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.core.management import call_command
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, FormView
from django.views.generic.edit import FormMixin
from django.contrib.auth.models import Group

from .forms import (
    BienForm,
    InterventionForm,
    ContactSiteForm,
    ContactAnnonceForm,
    BailForm,
    EtatDesLieuxForm, LocataireCreationForm,
)
from .models import (
    Bien,
    Bail,
    Loyer,
    Intervention,
    Annonce,
    EtatDesLieux, Transaction,
)
from .permissions import (
    is_admin,
    is_bailleur,
    is_locataire,
    get_active_bail,
)
from .services.paiement import PaymentService
from .services.stats import DashboardService

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

        # queryset de base (sans filtres) pour remplir les villes
        base_qs = self.get_base_queryset()

        paginator = context.get("paginator")

        context.update({
            "types_bien": Bien.TYPE_CHOICES,
            "villes": (
                base_qs
                .values_list("bien__ville", flat=True)
                .distinct()
                .order_by("bien__ville")
            ),
            # nombre d'annonces APRÈS filtres (via le paginator)
            "annonces_count": paginator.count if paginator else 0,
        })
        return context


class AnnonceDetailView(FormMixin, DetailView):
    """Page de détail d'une annonce publique + formulaire de contact."""
    model = Annonce
    template_name = 'biens/annonce_detail.html'
    context_object_name = 'annonce'
    form_class = ContactAnnonceForm

    def get_queryset(self):
        return Annonce.objects.filter(
            statut='PUBLIE',
            bien__in=Bien.objects.disponibles(),
        ).select_related('bien', 'bien__proprietaire')

    def get_success_url(self):
        return reverse('annonce_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['annonces_similaires'] = Annonce.objects.filter(
            statut='PUBLIE',
            bien__in=Bien.objects.disponibles(),
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
    """Tableau de bord multi-rôles centralisé (délégué au service de stats)"""
    context = {"user": request.user}
    service = DashboardService()

    if is_admin(request.user):
        context["user_role"] = "ADMIN"
        context.update(service.get_admin_stats())

    elif is_bailleur(request.user):
        context["user_role"] = "BAILLEUR"
        context.update(service.get_bailleur_stats(request.user))

    elif is_locataire(request.user):
        bail = get_active_bail(request.user)
        context.update({
            "user_role": "LOCATAIRE",
            "bail": bail,
        })
        if bail:
            context["dernier_loyer"] = (
                Loyer.objects.filter(bail=bail)
                .order_by("-date_echeance")
                .first()
            )
    else:
        context["user_role"] = "AGENT"

    return render(request, "dashboard.html", context)


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
        'user_role': 'ADMIN' if is_admin(request.user) else 'BAILLEUR',
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

    # Définir le queryset de base selon le rôle
    if is_bailleur(request.user):
        biens_queryset = Bien.objects.filter(proprietaire=request.user)
    else:
        biens_queryset = Bien.objects.all()

    if request.method == "POST":
        form = BailForm(request.POST, request.FILES)
        form.fields["bien"].queryset = biens_queryset

        if form.is_valid():
            bail = form.save()

            # Génération automatique du contrat PDF
            try:
                from apps.core.services.contrat import sauvegarder_contrat
                sauvegarder_contrat(bail)
                messages.success(request, "Le bail a été créé avec succès et le contrat PDF généré.")
            except Exception as e:
                logger.error(f"Erreur lors de la génération du contrat PDF pour le bail {bail.id}: {e}")
                messages.warning(request, "Le bail a été créé, mais la génération du PDF a échoué.")

            return redirect("bail_detail", pk=bail.pk)
    else:
        form = BailForm()
        form.fields["bien"].queryset = biens_queryset

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

    loyers = bail.loyers.order_by("-date_echeance")
    etats = bail.etats_des_lieux.order_by("-date_realisation")

    # Pour le template : séparer entrée / sortie si besoin
    edl_entree = etats.filter(type_edl="ENTREE").first()
    edl_sortie = etats.filter(type_edl="SORTIE").first()

    # Déterminer le rôle de l'utilisateur
    if is_admin(request.user):
        user_role = "ADMIN"
    elif bail.bien.proprietaire == request.user:
        user_role = "BAILLEUR"
    else:
        user_role = "LOCATAIRE"

    context = {
        "bail": bail,
        "loyers": loyers,
        "etats": etats,
        "edl_entree": edl_entree,
        "edl_sortie": edl_sortie,
        "user_role": user_role,
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
    try:
        loyer.enregistrer_paiement(loyer.reste_a_payer)
        messages.success(
            request,
            f"Loyer de {loyer.bail.locataire} marqué comme payé et quittance attachée.",
        )
    except Exception as e:
        logger.error(f"Erreur lors du marquage du loyer {loyer_id}: {e}")
        messages.error(request, "Erreur lors du traitement du paiement.")

    return redirect('loyers_list')


@login_required
def download_quittance(request, loyer_id):
    """Téléchargement de quittance PDF (Admin ou Locataire concerné)"""
    loyer = get_object_or_404(
        Loyer.objects.select_related('bail__locataire'),
        id=loyer_id,
    )

    # Permissions : admin ou locataire concerné
    if not is_admin(request.user) and loyer.bail.locataire != request.user:
        raise PermissionDenied("Accès non autorisé à cette quittance.")

    if loyer.statut != 'PAYE':
        messages.error(request, "La quittance n'est disponible que pour les loyers payés.")
        return redirect('dashboard')

    # Génération à la volée si absente
    if not loyer.quittance:
        try:
            from apps.core.services.quittance import attacher_quittance
            attacher_quittance(loyer)
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la quittance pour le loyer {loyer.id}: {e}")
            messages.error(request, "Impossible de générer la quittance. Contactez l'administrateur.")
            return redirect('dashboard')

    # Vérifier que la quittance a bien été attachée
    if not loyer.quittance:
        messages.error(request, "La quittance n'est pas disponible pour le moment.")
        return redirect('dashboard')

    return FileResponse(
        loyer.quittance.open("rb"),
        content_type="application/pdf",
        filename=loyer.quittance.name.split('/')[-1],
        as_attachment=False,
    )


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
        if user_is_admin:
            messages.error(request, "Les administrateurs ne peuvent pas créer d'interventions.")
            return redirect('interventions_list')

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


# ============================================================================
# GESTION DES ÉTATS DES LIEUX
# ============================================================================

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

    instance = EtatDesLieux(
        bail=bail,
        type_edl=type_edl,
        date_realisation=timezone.now().date(),
    )

    # Désactiver les champs sensibles
    disabled_fields = ['bail', 'type_edl']

    if request.method == "POST":
        form = EtatDesLieuxForm(request.POST, request.FILES, instance=instance)
        for field_name in disabled_fields:
            if field_name in form.fields:
                form.fields[field_name].disabled = True

        if form.is_valid():
            form.save()
            messages.success(request, "L'état des lieux a été enregistré avec succès.")
            return redirect("bail_detail", pk=bail.pk)
    else:
        form = EtatDesLieuxForm(instance=instance)
        for field_name in disabled_fields:
            if field_name in form.fields:
                form.fields[field_name].disabled = True

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


@login_required
def initier_paiement(request, loyer_id):
    """Crée la transaction et redirige vers la page de simulation."""
    loyer = get_object_or_404(Loyer, id=loyer_id, bail__locataire=request.user)

    if loyer.statut == 'PAYE':
        messages.info(request, "Ce loyer est déjà payé.")
        return redirect('dashboard')

    # On utilise Wave par défaut pour la démo, ou on récupère via POST
    provider = request.POST.get('provider', 'WAVE')

    service = PaymentService()
    transaction = service.creer_transaction(loyer, provider)

    # Redirection vers notre "fausse" page de paiement
    return redirect('simulation_paiement_gateway', transaction_id=transaction.id)


@login_required
def simulation_paiement_gateway(request, transaction_id):
    """Page factice qui simule l'interface de Wave ou Orange Money."""
    transaction = get_object_or_404(Transaction, id=transaction_id, loyer__bail__locataire=request.user)

    if request.method == 'POST':
        # L'utilisateur clique sur "Confirmer le paiement" sur la fausse page
        service = PaymentService()
        succes = service.valider_transaction(transaction.id)

        if succes:
            messages.success(request, f"Paiement de {transaction.montant} FCFA validé avec succès !")
            return redirect('dashboard')
        else:
            messages.error(request, "Erreur lors de la validation du paiement.")
            return redirect('dashboard')

    return render(request, 'paiements/simulation_gateway.html', {'transaction': transaction})
@login_required
def add_locataire(request):
    # Vérification permission admin
    if not is_admin(request.user):
        raise PermissionDenied("Accès réservé.")

    if request.method == 'POST':
        form = LocataireCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  # Cela sauvegarde User ET UserProfile grâce à notre formulaire modifié

            # Assigner le groupe LOCATAIRE
            group, _ = Group.objects.get_or_create(name='LOCATAIRE')
            user.groups.add(group)

            messages.success(request,
                             f"Locataire {user.first_name} créé avec succès (Téléphone : {user.profile.telephone}).")
            return redirect('dashboard')
    else:
        form = LocataireCreationForm()

    return render(request, 'utilisateurs/add_locataire.html', {
        'form': form,
        'user_role': 'ADMIN'
    })