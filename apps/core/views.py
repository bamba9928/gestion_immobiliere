from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render

from .models import Bail, Bien, Loyer


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
