from datetime import date
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
import weasyprint
from django.contrib import messages
from .forms import InterventionForm
from .models import Intervention, Bail
from .models import Bail, Bien, Loyer

@login_required
def dashboard(request):
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
        # Utilisez .first() car le tri est descendant ('-date_debut')
        bail = Bail.objects.filter(locataire=request.user, est_signe=True).first()

        context['bail'] = bail
        if bail:
            # On récupère la dernière quittance générée ou le prochain loyer
            dernier_loyer = Loyer.objects.filter(bail=bail).order_by('-date_echeance').first()
            context['dernier_loyer'] = dernier_loyer

        context['user_role'] = 'LOCATAIRE'

    return render(request, 'dashboard.html', context)
@login_required
def download_quittance(request, loyer_id: int) -> HttpResponse:
    loyer = get_object_or_404(Loyer, id=loyer_id)

    if not request.user.is_staff and loyer.bail.locataire != request.user:
        raise PermissionDenied("Vous n'avez pas accès à ce document.")
    if loyer.statut != 'PAYE':
        return HttpResponse(
            "Ce loyer n'est pas encore soldé. Impossible d'éditer la quittance.",
            status=400,
        )

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


@login_required
def interventions_list(request):
    # On récupère le bail actif du locataire
    bail = Bail.objects.filter(locataire=request.user, est_signe=True).first()

    if not bail:
        # Gestion du cas où l'utilisateur n'est pas locataire
        if request.user.is_staff:
            # Admin : voit tout (ou redirige vers l'admin panel)
            interventions = Intervention.objects.all()
        else:
            return render(request, 'interventions/pas_de_bail.html')
    else:
        # Locataire : voit ses demandes pour ce bien
        interventions = Intervention.objects.filter(bien=bail.bien, locataire=request.user)

    if request.method == 'POST':
        form = InterventionForm(request.POST, request.FILES)
        if form.is_valid():
            if not bail:
                messages.error(request, "Aucun bail actif associé.")
            else:
                intervention = form.save(commit=False)
                intervention.locataire = request.user
                intervention.bien = bail.bien
                intervention.save()
                messages.success(request, "Votre signalement a été enregistré.")
                # On redirige pour éviter la resoumission si on rafraîchit
                return render(request, 'interventions/liste.html', {
                    'interventions': interventions,  # Liste mise à jour
                    'form': InterventionForm()  # Formulaire vidé
                })
    else:
        form = InterventionForm()

    return render(request, 'interventions/liste.html', {
        'interventions': interventions,
        'form': form,
        'user_role': 'LOCATAIRE' if bail else 'AUTRE'
    })