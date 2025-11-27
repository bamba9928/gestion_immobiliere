from datetime import date
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib import messages
from django.core.management import call_command
import weasyprint

# Models
from .models import Bien, Bail, Loyer, Intervention

# Forms
from .forms import InterventionForm

# Permissions
from .permissions import (
    is_admin,
    is_bailleur,
    is_locataire,
    is_agent
)


# ============================================================================
# UTILITAIRES BAIL (équivalent du BailRequiredMixin pour vues fonctionnelles)
# ============================================================================

def get_active_bail(user):
    """
    Récupère le bail actif d'un utilisateur (dates valides et signé).
    Retourne None si aucun bail actif.
    """
    today = date.today()
    return user.baux.filter(
        est_signe=True,
        date_debut__lte=today,
        date_fin__gte=today,
    ).first()


def require_active_bail(user, message="Aucun bail actif trouvé."):
    """
    Vérifie qu'un utilisateur a un bail actif, lève PermissionDenied sinon.
    """
    bail = get_active_bail(user)
    if not bail:
        raise PermissionDenied(message)
    return bail


# ============================================================================
# VUES ADMINISTRATIVES
# ============================================================================

@login_required
def trigger_rent_generation(request):
    """Vue pour générer les loyers via commande admin."""
    if not is_admin(request.user):
        raise PermissionDenied("Accès administrateur requis.")

    try:
        call_command('generer_loyers')
        messages.success(request, "✅ Génération des loyers effectuée avec succès.")
    except Exception as e:
        messages.error(request, f"❌ Erreur lors de la génération : {str(e)}")

    return redirect('dashboard')


@login_required
def dashboard(request):
    """Tableau de bord multi-rôles."""
    context = {'user': request.user}

    # ADMINISTRATEUR
    if is_admin(request.user):
        context.update({
            'user_role': 'ADMIN',
            'total_biens': Bien.objects.count(),
            'biens_occupes': Bien.objects.filter(
                baux__est_signe=True,
                baux__date_fin__gte=date.today(),
            ).distinct().count(),
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

    # Calcul du taux d'occupation pour admin/bailleur
    if 'total_biens' in context and context['total_biens']:
        context['taux_occupation'] = int(
            (context['biens_occupes'] / context['total_biens']) * 100
        )

    return render(request, 'dashboard.html', context)


# ============================================================================
# VUES DOCUMENTS
# ============================================================================

@login_required
def download_quittance(request, loyer_id: int) -> HttpResponse:
    """Téléchargement de quittance PDF uniquement si payée."""
    loyer = get_object_or_404(Loyer, id=loyer_id)

    # Sécurité : admin ou locataire concerné
    if not is_admin(request.user) and loyer.bail.locataire != request.user:
        raise PermissionDenied("Accès non autorisé à cette quittance.")

    if loyer.statut != 'PAYE':
        messages.error(request, "⚠️ La quittance n'est disponible que pour les loyers payés.")
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
# VUES INTERVENTIONS (refactorisées)
# ============================================================================

@login_required
def interventions_list(request):
    """Liste et création d'interventions pour locataires."""

    # Récupération du bail actif
    bail = get_active_bail(request.user)

    # ADMIN : voit tout
    if is_admin(request.user):
        interventions = Intervention.objects.all().order_by('-created_at')
        user_role = 'ADMIN'
    # LOCATAIRE avec bail : voit ses interventions
    elif bail:
        interventions = Intervention.objects.filter(
            bien=bail.bien,
            locataire=request.user
        ).order_by('-created_at')
        user_role = 'LOCATAIRE'
    # UTILISATEUR SANS BAIL
    else:
        return render(request, 'interventions/pas_de_bail.html', {
            'message': "Vous n'avez aucun bail actif."
        })

    # Gestion du formulaire (POST uniquement pour locataires)
    if request.method == 'POST':
        # Vérification que c'est bien un locataire avec bail
        if not bail:
            messages.error(request, "❌ Aucun bail actif associé.")
            return redirect('interventions_list')

        form = InterventionForm(request.POST, request.FILES)
        if form.is_valid():
            intervention = form.save(commit=False)
            intervention.locataire = request.user
            intervention.bien = bail.bien
            intervention.save()
            messages.success(request, "✅ Demande d'intervention enregistrée avec succès.")
            return redirect('interventions_list')  # Pattern PRG
    else:
        form = InterventionForm()

    return render(request, 'interventions/liste.html', {
        'interventions': interventions,
        'form': form,
        'user_role': user_role,
        'bail': bail if not is_admin(request.user) else None,
    })