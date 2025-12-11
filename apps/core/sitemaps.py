from django.contrib.sitemaps import Sitemap
from apps.core.models import Bien

class BienSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8
    protocol = 'https'

    def items(self):
        # On ne veut indexer que les biens disponibles (et non supprimés)
        return Bien.objects.filter(is_disponible=True, deleted_at__isnull=True)

    def lastmod(self, obj):
        return obj.updated_at

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = "monthly"
    protocol = 'https'

    def items(self):
        return ['home', 'about', 'contact', 'login']

    def location(self, item):
        from django.urls import reverse
        return reverse(item)