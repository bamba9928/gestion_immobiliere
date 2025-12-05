# apps/core/services/contrat.py
import logging

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

logger = logging.getLogger(__name__)


def generer_contrat_bail_pdf(bail):
    """Génère le contenu PDF du contrat de bail."""
    context = {
        'bail': bail,
        'date_generation': timezone.now(),
    }

    html_string = render_to_string('documents/contrat_bail.html', context)

    # Base URL nécessaire pour charger les images/css si présents
    pdf_bytes = HTML(string=html_string, base_url=str(settings.BASE_DIR)).write_pdf()

    # Nom de fichier propre : Bail_ID_NOM.pdf
    nom_fichier = f"Bail_{bail.id}_{bail.locataire.username}.pdf".replace(" ", "_")

    return pdf_bytes, nom_fichier


def sauvegarder_contrat(bail):
    """Génère le PDF et l'attache à l'instance de Bail."""
    try:
        pdf_content, nom_fichier = generer_contrat_bail_pdf(bail)

        # save=True déclenche l'enregistrement en base
        bail.fichier_contrat.save(nom_fichier, ContentFile(pdf_content), save=True)
        return True
    except Exception as e:
        logger.error(f"Erreur génération contrat bail {bail.id}: {e}")
        return False