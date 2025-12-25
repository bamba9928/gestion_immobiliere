import logging
import os
from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

logger = logging.getLogger(__name__)


def generer_contrat_bail_pdf(bail):
    # 1. Chemin absolu vers le logo (doit correspondre au fichier uploadé 'mada.png')
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'mada.png')

    # Vérification optionnelle pour éviter un crash si l'image manque
    if not os.path.exists(logo_path):
        logger.warning(f"Logo introuvable pour le PDF: {logo_path}")
        # On peut mettre une image vide ou par défaut si besoin, ou laisser WeasyPrint gérer l'erreur

    context = {
        'bail': bail,
        'date_generation': timezone.now(),
        # 2. On passe le chemin absolu avec le protocole file:// pour WeasyPrint
        'logo_path': 'file://' + logo_path,
    }

    html_string = render_to_string('documents/contrat_bail.html', context)

    # base_url aide à résoudre les liens relatifs si besoin
    pdf_bytes = HTML(string=html_string, base_url=str(settings.BASE_DIR)).write_pdf()

    nom_fichier = f"Bail_{bail.id}_{bail.locataire.last_name}.pdf"
    return pdf_bytes, nom_fichier


def sauvegarder_contrat(bail):
    """Génère le PDF et l'attache à l'instance de Bail."""
    try:
        pdf_content, nom_fichier = generer_contrat_bail_pdf(bail)

        # save=True déclenche l'enregistrement en base
        # save=False ici pour éviter une double sauvegarde si on appelle save() juste après dans la vue
        # Mais dans votre cas, save=True est plus sûr si appelé depuis une tâche asynchrone
        bail.fichier_contrat.save(nom_fichier, ContentFile(pdf_content), save=True)
        return True
    except Exception as e:
        logger.error(f"Erreur génération contrat bail {bail.id}: {e}")
        return False