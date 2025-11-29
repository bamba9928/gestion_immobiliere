from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML


def generer_quittance_pdf(loyer):
    """Retourne le contenu PDF de la quittance ainsi que le nom de fichier."""
    html_string = render_to_string(
        'documents/quittance.html',
        {
            'loyer': loyer,
            'now': timezone.now(),
        },
    )

    pdf_bytes = HTML(string=html_string, base_url=str(settings.BASE_DIR)).write_pdf()
    filename = (
        f"Quittance_{loyer.periode_debut.strftime('%Y-%m')}"
        f"_{loyer.bail.locataire.username}.pdf"
    )
    return pdf_bytes, filename


def attacher_quittance(loyer):
    """Génère et sauvegarde la quittance PDF sur l'objet Loyer fourni."""
    pdf_content, filename = generer_quittance_pdf(loyer)
    loyer.quittance.save(filename, ContentFile(pdf_content), save=False)
    loyer.save(update_fields=["quittance"])
    return filename