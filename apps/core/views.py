import logging
import mimetypes
from datetime import date
from itertools import chain
from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.core.management import call_command
from django.db.models import Q, Sum
from django.http import FileResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, FormView
from django.views.generic.edit import FormMixin
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from django.http import HttpResponse

from .forms import (
    BienForm,
    InterventionForm,
    ContactSiteForm,
    ContactAnnonceForm,
    BailForm,
    EtatDesLieuxForm,
    LocataireCreationForm,
    DepenseForm,
)
from .models import (
    Bien,
    Bail,
    Loyer,
    Intervention,
    Annonce,
    EtatDesLieux,
    Transaction,
    Depense,
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
    model = Annonce
    template_name = 'home.html'
    context_object_name = 'annonces'
    paginate_by = 9

    def get_base_queryset(self):
        return Annonce.objects.filter(
            statut='PUBLIE',
            bien__in=Bien.objects.disponibles()
        ).select_related('bien', 'bien__proprietaire')

    def get_queryset(self):
        queryset = self.get_base_queryset()

        if q := self.request.GET.get("q"):
            queryset = queryset.filter(
                Q(bien__ville__icontains=q)
                | Q(bien__adresse__icontains=q)
                | Q(titre__icontains=q)
                | Q(description__icontains=q)
            )

        if type_bien := self.request.GET.get("type"):
            queryset = queryset.filter(bien__type_bien=type_bien)

        if ville := self.request.GET.get("ville"):
            queryset = queryset.filter(bien__ville=ville)

        if prix_max := self.request.GET.get("prix_max"):
            queryset = queryset.filter(prix__lte=prix_max)

        allowed_sorts = ["-date_publication", "date_publication", "prix", "-prix"]
        sort = self.request.GET.get("sort", "-date_publication")
        if sort not in allowed_sorts:
            sort = "-date_publication"

        return queryset.order_by(sort)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
            "annonces_count": paginator.count if paginator else 0,
        })
        return context


class AnnonceDetailView(FormMixin, DetailView):
    model = Annonce
    template_name = 'biens/annonce_detail.html'
    context_object_name = 'annonce'
    form_class = ContactAnnonceForm
    query_pk_and_slug = False

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

@login_required
def grand_livre(request):
    # =======================================================
    # MODIFICATION : Restriction stricte à l'ADMINISTRATEUR
    # =======================================================
    if not is_admin(request.user):
        raise PermissionDenied("Accès réservé aux administrateurs.")

    try:
        annee = int(request.GET.get("annee", date.today().year))
    except (TypeError, ValueError):
        annee = date.today().year

    # 1. Recettes (Transactions validées)
    recettes = Transaction.objects.filter(
        est_validee=True,
        created_at__year=annee,
    ).select_related("loyer__bail__bien")

    # 2. Dépenses
    depenses = Depense.objects.filter(
        date_paiement__year=annee,
    ).select_related("bien")

    # Note: La logique de filtrage 'proprietaire' a été retirée car seul l'admin accède ici.
    # L'admin voit TOUT.

    total_recettes = recettes.aggregate(Sum("montant"))["montant__sum"] or 0
    total_depenses = depenses.aggregate(Sum("montant"))["montant__sum"] or 0
    cash_flow = total_recettes - total_depenses

    for r in recettes:
        r.flux = "CREDIT"
        r.date_ope = r.created_at.date()
        r.libelle_comptable = (
            f"Loyer {r.loyer.periode_debut.strftime('%m/%Y')} "
            f"- {r.loyer.bail.locataire.last_name}"
        )

    for d in depenses:
        d.flux = "DEBIT"
        d.date_ope = d.date_paiement
        d.libelle_comptable = f"{d.get_type_depense_display()} : {d.libelle}"

    mouvements = sorted(
        chain(recettes, depenses),
        key=lambda x: x.date_ope,
        reverse=True,
    )
    # Années disponibles (à partir des données réelles)
    annees_recettes = Transaction.objects.filter(
        est_validee=True
    ).dates("created_at", "year")

    annees_depenses = Depense.objects.all().dates("date_paiement", "year")

    annees_disponibles = sorted(
        {d.year for d in chain(annees_recettes, annees_depenses)},
        reverse=True,
    )
    if not annees_disponibles:
        annees_disponibles = [annee]
    return render(
        request,
        "comptabilite/grand_livre.html",
        {
            "mouvements": mouvements,
            "total_recettes": total_recettes,
            "total_depenses": total_depenses,
            "cash_flow": cash_flow,
            "annee_courante": annee,
            "annees_disponibles": annees_disponibles,
        },
    )
# ============================================================================
# TABLEAU DE BORD & GESTION (Protégé par login)
# ============================================================================

@login_required
def dashboard(request):
    """Tableau de bord multi-rôles centralisé (délégué au service de stats)"""
    context = {"user": request.user, "today": date.today()}
    service = DashboardService()

    if is_admin(request.user):
        context["user_role"] = "ADMIN"
        context.update(service.get_admin_stats())

    elif is_bailleur(request.user):
        context["user_role"] = "BAILLEUR"
        # On appelle la nouvelle méthode pour le bailleur
        context.update(service.get_bailleur_stats(request.user))

    elif is_locataire(request.user):
        bail = get_active_bail(request.user)

        if bail:
            loyers_qs = (
                Loyer.objects.filter(bail=bail)
                .order_by("-date_echeance")
            )
            dernier_loyer = loyers_qs.first()

            interventions_qs = (
                Intervention.objects.filter(
                    bien=bail.bien,
                    locataire=request.user,
                )
                .select_related("bien")
                .order_by("-created_at")[:5]
            )
        else:
            loyers_qs = Loyer.objects.none()
            dernier_loyer = None
            interventions_qs = Intervention.objects.none()

        context.update(
            {
                "user_role": "LOCATAIRE",
                "bail": bail,
                "loyers": loyers_qs,
                "dernier_loyer": dernier_loyer,
                "interventions_recents": interventions_qs,
                "has_active_bail": bool(bail),
            }
        )
    else:
        # Agent ou autre
        context["user_role"] = "AGENT"

    return render(request, "dashboard.html", context)


@login_required
def add_bien(request):
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
# apps/core/views.py

from django.db.models import Sum

@login_required
def gestion_bien_detail(request, pk):
    """
    Vue tableau de bord pour un bien spécifique (Vue Propriétaire/Admin).
    """
    bien = get_object_or_404(Bien, pk=pk)

    # Sécurité : Seul le propriétaire ou l'admin peut voir cette page
    if not (is_admin(request.user) or bien.proprietaire == request.user):
        raise PermissionDenied("Vous n'êtes pas propriétaire de ce bien.")

    # 1. Récupérer le bail actif (s'il y en a un)
    bail_actif = bien.baux.filter(date_fin__isnull=True).order_by('-date_debut').first()

    # 2. Historique des interventions
    interventions = bien.interventions.select_related('locataire').order_by('-created_at')[:5]

    # 3. Calculs financiers pour CE bien
    # Total des loyers encaissés (liés aux baux de ce bien)
    total_recettes = Transaction.objects.filter(
        loyer__bail__bien=bien,
        est_validee=True
    ).aggregate(Sum('montant'))['montant__sum'] or 0

    # Total des dépenses liées à ce bien
    total_depenses = Depense.objects.filter(
        bien=bien
    ).aggregate(Sum('montant'))['montant__sum'] or 0

    cash_flow = total_recettes - total_depenses

    # 4. Taux d'occupation (Calcul simple basé sur l'existence d'un bail actif)
    est_loue = bail_actif is not None

    context = {
        'bien': bien,
        'bail_actif': bail_actif,
        'interventions': interventions,
        'total_recettes': total_recettes,
        'total_depenses': total_depenses,
        'cash_flow': cash_flow,
        'est_loue': est_loue,
    }
    return render(request, 'biens/gestion_detail.html', context)
@login_required
def add_bail(request):
    if not (is_admin(request.user) or is_bailleur(request.user)):
        raise PermissionDenied("Seuls les administrateurs et bailleurs peuvent créer un bail.")

    if is_bailleur(request.user):
        biens_queryset = Bien.objects.filter(proprietaire=request.user)
    else:
        biens_queryset = Bien.objects.all()

    if request.method == "POST":
        form = BailForm(request.POST, request.FILES)
        form.fields["bien"].queryset = biens_queryset

        if form.is_valid():
            bail = form.save()
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
    bail = get_object_or_404(Bail, pk=pk)

    if not (
            is_admin(request.user)
            or bail.bien.proprietaire == request.user
            or bail.locataire == request.user
    ):
        raise PermissionDenied("Vous n'avez pas l'autorisation de consulter ce bail.")

    loyers = bail.loyers.order_by("-date_echeance")
    etats = bail.etats_des_lieux.order_by("-date_realisation")
    edl_entree = etats.filter(type_edl="ENTREE").first()
    edl_sortie = etats.filter(type_edl="SORTIE").first()

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


@login_required
def loyers_list(request):
    if not is_admin(request.user):
        raise PermissionDenied("Accès réservé aux administrateurs.")

    statut = request.GET.get("statut")
    base_qs = Loyer.objects.select_related("bail__locataire", "bail__bien")
    loyers = base_qs.order_by("-date_echeance")

    if statut:
        loyers = loyers.filter(statut=statut)

    stats = {
        "total_retard": base_qs.filter(statut="RETARD").count(),
        "total_attente": base_qs.filter(statut="A_PAYER").count(),
    }

    return render(
        request,
        "interventions/loyers_list.html",
        {
            "loyers": loyers,
            "current_statut": statut,
            "stats": stats,
        },
    )


@login_required
def mark_loyer_paid(request, loyer_id):
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
    loyer = get_object_or_404(
        Loyer.objects.select_related('bail__locataire'),
        id=loyer_id,
    )

    if not is_admin(request.user) and loyer.bail.locataire != request.user:
        raise PermissionDenied("Accès non autorisé à cette quittance.")

    if loyer.statut != 'PAYE':
        messages.error(request, "La quittance n'est disponible que pour les loyers payés.")
        return redirect('dashboard')

    if not loyer.quittance:
        try:
            from apps.core.services.quittance import attacher_quittance
            attacher_quittance(loyer)
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la quittance pour le loyer {loyer.id}: {e}")
            messages.error(request, "Impossible de générer la quittance. Contactez l'administrateur.")
            return redirect('dashboard')

    if not loyer.quittance:
        messages.error(request, "La quittance n'est pas disponible pour le moment.")
        return redirect('dashboard')

    return FileResponse(
        loyer.quittance.open("rb"),
        content_type="application/pdf",
        filename=loyer.quittance.name.split('/')[-1],
        as_attachment=False,
    )


@login_required
def interventions_list(request):
    # 1. Détermination des rôles
    user_is_admin = is_admin(request.user)
    user_is_bailleur = is_bailleur(request.user)

    # 2. Récupération du bail (uniquement utile si c'est un locataire)
    bail = None
    if not user_is_admin and not user_is_bailleur:
        bail = get_active_bail(request.user)

    # 3. Filtrage des interventions (QuerySet)
    if user_is_admin:
        # L'admin voit TOUT
        interventions = Intervention.objects.select_related(
            'bien', 'locataire', 'bien__proprietaire'
        ).all().order_by('-created_at')

    elif user_is_bailleur:
        # Le bailleur voit les interventions sur SES biens
        interventions = Intervention.objects.filter(
            bien__proprietaire=request.user
        ).select_related('bien', 'locataire').order_by('-created_at')

    elif bail:
        # Le locataire voit les interventions sur SON logement (via le bail)
        interventions = Intervention.objects.filter(
            bien=bail.bien,
            locataire=request.user
        ).select_related('bien').order_by('-created_at')

    else:
        # Ni admin, ni bailleur, et pas de bail actif
        return render(request, 'interventions/pas_de_bail.html', {
            'message': "Vous n'avez aucun bail actif."
        })

    # 4. Gestion du formulaire (Création)
    form = InterventionForm()

    if request.method == 'POST':
        # On empêche l'admin et le bailleur de créer une demande via cette vue
        # (C'est généralement le locataire qui signale un problème ici)
        if user_is_admin or user_is_bailleur:
            messages.error(request, "Seuls les locataires peuvent créer une demande d'intervention ici.")
            return redirect('interventions_list')

        if not bail:
            messages.error(request, "Impossible de créer une intervention sans bail actif.")
            return redirect('interventions_list')

        form = InterventionForm(request.POST, request.FILES)
        if form.is_valid():
            intervention = form.save(commit=False)
            intervention.locataire = request.user
            # On lie l'intervention au bien du bail courant
            intervention.bien = bail.bien
            intervention.save()
            messages.success(request, "Demande d'intervention enregistrée avec succès.")
            return redirect('interventions_list')

    # 5. Détermination du rôle pour le template (affichage conditionnel)
    if user_is_admin:
        role_str = 'ADMIN'
    elif user_is_bailleur:
        role_str = 'BAILLEUR'
    else:
        role_str = 'LOCATAIRE'

    return render(request, 'interventions/interventions_list.html', {
        'interventions': interventions,
        'form': form,
        'user_role': role_str,
        'bail': bail,  # Sera None pour admin et bailleur
    })
@login_required
def add_etat_des_lieux(request, bail_id, type_edl):
    bail = get_object_or_404(Bail, pk=bail_id)

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


@login_required
def trigger_rent_generation(request):
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
    if request.method != "POST":
        messages.warning(request, "Méthode non autorisée.")
        return redirect("dashboard")

    loyer = get_object_or_404(Loyer, id=loyer_id, bail__locataire=request.user)

    if loyer.statut == "PAYE":
        messages.info(request, "Ce loyer est déjà payé.")
        return redirect("dashboard")

    provider = request.POST.get("provider", "WAVE")
    service = PaymentService()
    transaction = service.creer_transaction(loyer, provider)

    return redirect("simulation_paiement_gateway", transaction_id=transaction.id)


@login_required
def simulation_paiement_gateway(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id, loyer__bail__locataire=request.user)

    if request.method == 'POST':
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
    if not is_admin(request.user):
        raise PermissionDenied("Accès réservé.")

    if request.method == 'POST':
        form = LocataireCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
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


@login_required
def add_depense(request):
    if not (is_admin(request.user) or is_bailleur(request.user)):
        raise PermissionDenied("Vous n'avez pas les droits pour ajouter une dépense.")

    if request.method == 'POST':
        form = DepenseForm(request.POST, request.FILES)
        if is_bailleur(request.user):
            form.fields['bien'].queryset = Bien.objects.filter(proprietaire=request.user)

        if form.is_valid():
            depense = form.save()
            messages.success(request, f"Dépense '{depense.libelle}' enregistrée avec succès.")
            # Redirection conditionnelle: le bailleur n'a pas accès au grand livre
            if is_admin(request.user):
                return redirect('grand_livre')
            else:
                return redirect('dashboard')
        else:
            messages.error(request, "Erreur dans le formulaire. Veuillez vérifier les champs.")

    else:
        form = DepenseForm()
        if is_bailleur(request.user):
            form.fields['bien'].queryset = Bien.objects.filter(proprietaire=request.user)

    return render(request, 'comptabilite/add_depense.html', {
        'form': form,
        'user_role': 'ADMIN' if is_admin(request.user) else 'BAILLEUR',
    })
@login_required
def add_bailleur(request):
    if not is_admin(request.user):
        raise PermissionDenied("Accès réservé.")

    if request.method == 'POST':
        form = LocataireCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            group, _ = Group.objects.get_or_create(name='BAILLEUR')
            user.groups.add(group)

            messages.success(
                request,
                f"Bailleur {user.get_full_name() or user.username} créé avec succès."
            )
            return redirect('dashboard')
    else:
        form = LocataireCreationForm()

    return render(request, 'utilisateurs/add_bailleur.html', {
        'form': form,
        'user_role': 'ADMIN',
    })
@login_required
def add_agent(request):
    if not is_admin(request.user):
        raise PermissionDenied("Accès réservé.")

    if request.method == 'POST':
        form = LocataireCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            group, _ = Group.objects.get_or_create(name='AGENT')
            user.groups.add(group)

            messages.success(
                request,
                f"Agent {user.get_full_name() or user.username} créé avec succès."
            )
            return redirect('dashboard')
    else:
        form = LocataireCreationForm()

    return render(request, 'utilisateurs/add_agent.html', {
        'form': form,
        'user_role': 'ADMIN',
    })

@login_required
def generate_lease_pdf(request, bail_id):
    bail = get_object_or_404(Bail, pk=bail_id)

    if not (is_admin(request.user) or bail.bien.proprietaire == request.user):
        raise PermissionDenied("Vous n'avez pas le droit de générer ce contrat.")

    try:
        from apps.core.services.contrat import sauvegarder_contrat
        sauvegarder_contrat(bail)
        messages.success(request, "Contrat PDF généré et attaché au bail.")
    except Exception as e:
        logger.error(f"Erreur génération contrat PDF pour le bail {bail.id}: {e}")
        messages.error(request, "Impossible de générer le contrat. Contactez l'administrateur.")

    return redirect("bail_detail", pk=bail.pk)
@login_required
def download_contrat(request, bail_id):
    """
    Vue sécurisée pour télécharger le contrat de bail.
    Vérifie que l'utilisateur est soit l'admin, le propriétaire ou le locataire.
    """
    bail = get_object_or_404(Bail, pk=bail_id)

    # Vérification stricte des droits
    is_proprio = (bail.bien.proprietaire == request.user)
    is_locataire = (bail.locataire == request.user)

    if not (is_admin(request.user) or is_proprio or is_locataire):
        raise PermissionDenied("Vous n'avez pas l'autorisation de télécharger ce contrat.")

    if not bail.fichier_contrat:
        raise Http404("Aucun contrat signé n'est disponible pour ce bail.")

    # Servir le fichier
    response = FileResponse(
        bail.fichier_contrat.open('rb'),
        content_type='application/pdf'
    )
    # 'inline' permet l'affichage dans le navigateur, 'attachment' force le téléchargement
    response['Content-Disposition'] = f'inline; filename="Bail_{bail.id}.pdf"'
    return response


@login_required
def download_kyc(request, user_id, doc_type):
    """
    Vue sécurisée pour télécharger les pièces d'identité (CNI, Justificatifs).
    Accès réservé à l'utilisateur lui-même ou à un administrateur.
    """
    User = get_user_model()
    target_user = get_object_or_404(User, pk=user_id)

    # Seul l'admin ou l'utilisateur concerné peut voir ses documents
    if not (is_admin(request.user) or request.user == target_user):
        raise PermissionDenied("Accès refusé aux documents personnels.")

    # Récupération du profil
    profile = getattr(target_user, 'profile', None)
    if not profile:
        raise Http404("Profil utilisateur introuvable.")

    # Sélection du fichier selon le type demandé
    file_obj = None
    if doc_type == 'cni':
        file_obj = profile.cni_scan
    elif doc_type == 'justificatif':
        file_obj = profile.justificatif_domicile

    if not file_obj:
        raise Http404("Document non trouvé.")

    # Détection du type MIME (pdf, jpg, png...)
    content_type, _ = mimetypes.guess_type(file_obj.name)
    if not content_type:
        content_type = 'application/octet-stream'

    return FileResponse(
        file_obj.open('rb'),
        content_type=content_type,
        filename=file_obj.name.split('/')[-1]
    )
@login_required
def export_grand_livre_excel(request):
    if not is_admin(request.user):
        raise PermissionDenied("Accès réservé aux administrateurs.")

    try:
        annee = int(request.GET.get("annee", date.today().year))
    except (TypeError, ValueError):
        annee = date.today().year

    # 1. Récupération des données (identique à la vue grand_livre)
    recettes = Transaction.objects.filter(
        est_validee=True,
        created_at__year=annee,
    ).select_related("loyer__bail__bien", "loyer__bail__locataire")

    depenses = Depense.objects.filter(
        date_paiement__year=annee,
    ).select_related("bien")

    # 2. Préparation du fichier Excel
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename=Grand_Livre_{annee}.xlsx'

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Grand Livre {annee}"

    # Styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="10B981", end_color="10B981", fill_type="solid")  # Emerald-500
    center_align = Alignment(horizontal='center')
    currency_fmt = '#,##0 "FCFA"'

    # En-têtes
    headers = ["Date", "Type", "Libellé / Tiers", "Bien concerné", "Recette (Crédit)", "Dépense (Débit)"]
    ws.append(headers)

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    # 3. Remplissage des données
    row_num = 2

    # Recettes
    for r in recettes:
        libelle = f"Loyer {r.loyer.periode_debut.strftime('%m/%Y')} - {r.loyer.bail.locataire.get_full_name()}"
        ws.append([
            r.created_at.date(),
            "RECETTE",
            libelle,
            r.loyer.bail.bien.titre,
            r.montant,
            0
        ])

    # Dépenses
    for d in depenses:
        ws.append([
            d.date_paiement,
            "DEPENSE",
            f"{d.get_type_depense_display()} : {d.libelle}",
            d.bien.titre,
            0,
            d.montant
        ])

    # Tri par date (via Excel si on voulait, mais ici on append juste.
    # Pour faire propre, on pourrait trier la liste combinée en Python avant d'écrire)

    # Ajustement colonnes
    column_widths = [15, 15, 40, 30, 20, 20]
    for i, width in enumerate(column_widths):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i + 1)].width = width

    wb.save(response)
    return response
@login_required
def documents_list(request):
    user = request.user

    # Initialisation des listes
    baux = []
    quittances = []
    edls = []  # États des lieux

    if is_admin(user):
        baux = (
            Bail.objects
            .select_related('bien', 'locataire')
            .filter(fichier_contrat__isnull=False)
            .exclude(fichier_contrat='')
        )
        quittances = (
            Loyer.objects
            .select_related('bail__locataire')
            .filter(quittance__isnull=False)
            .exclude(quittance='')
        )
        edls = (
            EtatDesLieux.objects
            .select_related('bail__bien')
            .filter(pdf__isnull=False)
            .exclude(pdf='')
        )
    elif is_bailleur(user):
        biens_ids = Bien.objects.filter(proprietaire=user).values_list('id', flat=True)
        baux = (
            Bail.objects
            .filter(bien_id__in=biens_ids)
            .select_related('locataire', 'bien')
            .filter(fichier_contrat__isnull=False)
            .exclude(fichier_contrat='')
        )
        quittances = (
            Loyer.objects
            .filter(bail__bien_id__in=biens_ids)
            .select_related('bail__locataire', 'bail__bien')
            .filter(quittance__isnull=False)
            .exclude(quittance='')
        )
        edls = (
            EtatDesLieux.objects
            .filter(bail__bien_id__in=biens_ids)
            .select_related('bail__bien')
            .filter(pdf__isnull=False)
            .exclude(pdf='')
        )

    # CORRECTION : Un seul bloc pour le locataire
    elif is_locataire(user):
        baux = (
            Bail.objects
            .filter(locataire=user)
            .select_related('bien')
            .filter(fichier_contrat__isnull=False)
            .exclude(fichier_contrat='')
        )
        quittances = (
            Loyer.objects
            .filter(bail__locataire=user)
            .select_related('bail__bien')
            .filter(quittance__isnull=False)
            .exclude(quittance='')
        )
        edls = (
            EtatDesLieux.objects
            .filter(bail__locataire=user)
            .select_related('bail__bien')
            .filter(pdf__isnull=False)
            .exclude(pdf='')
        )

    context = {
        'baux': baux,
        'quittances': quittances,
        'edls': edls,
    }
    return render(request, 'documents/ged_list.html', context)