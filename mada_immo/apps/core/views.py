"""
Views for the core application.

This module contains views for displaying the dashboard and generating
PDF quittances. Access control is enforced via decorators to ensure
authenticated access and to restrict tenants from downloading
documents that do not belong to them.
"""
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
import weasyprint

from .models import Bail, Bien, Loyer


@login_required
def dashboard(request):
    """
    Render a dashboard with key indicators based on the user's role.

    - Administrators see global metrics across all properties.
    - Owners (bailleurs) see metrics scoped to their own portfolio.
    - Tenants (locataires) see a summary of their current lease and latest rent.

    The appropriate role is inferred using ``request.user.is_staff`` to
    identify administrators, the presence of owned properties to identify
    owners, and otherwise the user is assumed to be a tenant.
    """
    context: dict[str, object] = {}
    # Administrator dashboard
    if request.user.is_staff:
        total_biens = Bien.objects.count()
        biens_occupes = Bien.objects.filter(
            baux__est_signe=True,
            baux__date_fin__gte=date.today(),
        ).distinct().count()
        context.update({
            'total_biens': total_biens,
            'biens_occupes': biens_occupes,
            'taux_occupation': int((biens_occupes / total_biens) * 100) if total_biens else 0,
            'montant_impayes': Loyer.objects.filter(statut='RETARD').aggregate(total=Sum('montant_du'))['total'] or 0,
            'user_role': 'ADMIN',
        })
    # Owner dashboard
    elif Bien.objects.filter(proprietaire=request.user).exists():
        # Filter metrics to the properties owned by the current user
        biens_proprio = Bien.objects.filter(proprietaire=request.user)
        total_biens = biens_proprio.count()
        biens_occupes = biens_proprio.filter(
            baux__est_signe=True,
            baux__date_fin__gte=date.today(),
        ).distinct().count()
        montant_impayes = Loyer.objects.filter(
            bail__bien__proprietaire=request.user,
            statut='RETARD',
        ).aggregate(total=Sum('montant_du'))['total'] or 0
        context.update({
            'total_biens': total_biens,
            'biens_occupes': biens_occupes,
            'taux_occupation': int((biens_occupes / total_biens) * 100) if total_biens else 0,
            'montant_impayes': montant_impayes,
            'user_role': 'BAILLEUR',
        })
    # Tenant dashboard
    else:
        bail = Bail.objects.filter(locataire=request.user, est_signe=True).last()
        context['bail'] = bail
        if bail:
            dernier_loyer = Loyer.objects.filter(bail=bail).order_by('-date_echeance').first()
            context['dernier_loyer'] = dernier_loyer
        context['user_role'] = 'LOCATAIRE'
    return render(request, 'dashboard.html', context)


@login_required
def download_quittance(request, loyer_id: int) -> HttpResponse:
    """Return a PDF quittance for a fully paid rent identified by ``loyer_id``.

    Only administrators or the tenant associated with the rent can access this view. If the
    rent isn't marked as paid, an explanatory error message is returned.
    """
    loyer = get_object_or_404(Loyer, id=loyer_id)
    # Authorization check
    if not request.user.is_staff and loyer.bail.locataire != request.user:
        raise PermissionDenied("Vous n'avez pas accès à ce document.")
    if loyer.statut != 'PAYE':
        return HttpResponse(
            "Ce loyer n'est pas encore soldé. Impossible d'éditer la quittance.",
            status=400,
        )
    # Render HTML template
    html_string = render_to_string(
        'documents/quittance.html',
        {
            'loyer': loyer,
            'now': timezone.now(),
        },
    )
    response = HttpResponse(content_type='application/pdf')
    filename = f"Quittance_{loyer.periode_debut.strftime('%Y-%m')}_{loyer.bail.locataire.username}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    weasyprint.HTML(string=html_string).write_pdf(response)
    return response
