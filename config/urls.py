from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from apps.core.sitemaps import BienSitemap, StaticViewSitemap
from django.views.generic import TemplateView

sitemaps = {
    'biens': BienSitemap,
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path("password_reset/",
         auth_views.PasswordResetView.as_view(),
         name="password_reset"),
    path("password_reset/done/",
         auth_views.PasswordResetDoneView.as_view(),
         name="password_reset_done"),
    path("reset/<uidb64>/<token>/",
         auth_views.PasswordResetConfirmView.as_view(),
         name="password_reset_confirm"),
    path("reset/done/",
         auth_views.PasswordResetCompleteView.as_view(),
         name="password_reset_complete"),
    path('', include('apps.core.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api/', include('apps.api.urls')),
    # SEO URLs
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)