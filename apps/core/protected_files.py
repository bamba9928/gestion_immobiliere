"""Liens vers les fichiers privés.

En production, nginx ne sert publiquement que ``/media/biens/`` (photos d'annonces) : tout le reste de
``/media/`` répond 404. Les autres fichiers (contrats, quittances, états des lieux, justificatifs, pièces
d'identité, photos d'interventions) ne sont lisibles que par les vues ``download_*`` de ``apps/core/views.py``,
qui vérifient les droits de l'utilisateur.

Ce module donne l'URL protégée qui correspond à un fichier, et fournit un widget d'administration qui
l'utilise à la place de ``file.url`` (lien « Actuellement : … » des formulaires de l'admin).
"""

from django.contrib.admin.widgets import AdminFileWidget
from django.urls import reverse

# (modèle, champ) -> (nom de la route, arguments de la route à partir de l'instance)
PROTECTED_URLS = {
    ("core.bail", "fichier_contrat"): ("download_contrat", lambda obj: [obj.pk]),
    ("core.loyer", "quittance"): ("download_quittance", lambda obj: [obj.pk]),
    ("core.etatdeslieux", "pdf"): ("download_edl", lambda obj: [obj.pk]),
    ("core.depense", "justificatif"): ("download_depense_justificatif", lambda obj: [obj.pk]),
}


def protected_url(field_file):
    """URL de la vue protégée qui sert ``field_file``, ou ``None`` si le fichier n'a pas de vue dédiée."""
    instance = getattr(field_file, "instance", None)
    if not field_file or instance is None:
        return None
    route = PROTECTED_URLS.get((instance._meta.label_lower, field_file.field.name))
    if route is None:
        return None
    name, get_args = route
    return reverse(name, args=get_args(instance))


class ProtectedFileWidget(AdminFileWidget):
    """Widget de fichier de l'admin dont le lien « Actuellement » passe par la vue protégée."""

    template_name = "admin/widgets/protected_file_input.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["protected_url"] = protected_url(value)
        return context
