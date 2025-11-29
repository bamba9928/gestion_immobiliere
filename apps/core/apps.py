from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Gestion immobilière"  # optionnel, pour l’admin

    def ready(self):
        # Import des signaux pour connecter les handlers
        import apps.core.signals  # noqa: F401
