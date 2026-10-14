from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.core.models import Annonce, Bien

class AnnonceSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8
    protocol = 'https'

    def items(self):
        # Mêmes annonces que la page publique annonce_detail : publiées, sur un bien disponible
        return Annonce.objects.filter(
            statut="PUBLIE",
            bien__in=Bien.objects.disponibles(),
        ).order_by("-updated_at")

    def location(self, obj):
        return reverse("annonce_detail", kwargs={"pk": obj.pk})

    def lastmod(self, obj):
        return obj.updated_at

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = "monthly"
    protocol = 'https'

    def items(self):
        return ['home', 'about', 'contact', 'login']

    def location(self, item):
        return reverse(item)
