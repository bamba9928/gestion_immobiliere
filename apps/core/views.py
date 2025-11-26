from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
import weasyprint
from django.utils import timezone

from .models import Bail, Bien, Loyer
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.core.exceptions import PermissionDenied

@login_required
def dashboard(request):
    context = {}

    # 2. Logique ADMIN (Superuser ou Staff)
    if request.user.is_staff:
        # KPIs globaux
        context['total_biens'] = Bien.objects.count()
        context['biens_occupes'] = Bien.objects.filter(baux__est_signe=True,
                                                       baux__date_fin__gte=date.today()).distinct().count()

        # Calcul du taux d'occupation (éviter division par zéro)
        if context['total_biens'] > 0:
            context['taux_occupation'] = int((context['biens_occupes'] / context['total_biens']) * 100)
        else:
            context['taux_occupation'] = 0

        # Finances : Loyers en retard ce mois-ci
        loyers_retard = Loyer.objects.filter(statut='RETARD').aggregate(total=Sum('montant_du'))
        context['montant_impayes'] = loyers_retard['total'] or 0

        context['user_role'] = 'ADMIN'

    # 3. Logique LOCATAIRE (Utilisateur standard)
    else:
        # Récupérer le bail actif
        bail = Bail.objects.filter(locataire=request.user, est_signe=True).last()
        context['bail'] = bail

        if bail:
            # Récupérer le dernier loyer émis
            dernier_loyer = Loyer.objects.filter(bail=bail).order_by('-date_echeance').first()
            context['dernier_loyer'] = dernier_loyer

        context['user_role'] = 'LOCATAIRE'

    return render(request, 'dashboard.html', context)


def download_quittance(request, loyer_id):
    # 1. Récupérer le loyer
    loyer = get_object_or_404(Loyer, id=loyer_id)

    # 2. Sécurité : Seul le locataire du bail ou un Admin peut télécharger
    if not request.user.is_staff and loyer.bail.locataire != request.user:
        raise PermissionDenied("Vous n'avez pas accès à ce document.")

    # 3. Vérifier que c'est bien payé (Optionnel, mais logique pour une quittance)
    if loyer.statut != 'PAYE':
        return HttpResponse("Ce loyer n'est pas encore soldé. Impossible d'éditer la quittance.", status=400)

    # 4. Générer le HTML
    html_string = render_to_string('documents/quittance.html', {
        'loyer': loyer,
        'now': timezone.now()
    })

    # 5. Convertir en PDF
    response = HttpResponse(content_type='application/pdf')
    # attachment; filename=... pour télécharger, inline; pour afficher dans le navigateur
    filename = f"Quittance_{loyer.periode_debut.strftime('%Y-%m')}_{loyer.bail.locataire.username}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    weasyprint.HTML(string=html_string).write_pdf(response)

    return response