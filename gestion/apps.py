from django.apps import AppConfig


class GestionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gestion'
    verbose_name = 'Gestión de Salón'

    def ready(self):
        import gestion.signals  # noqa: F401 — registra los receivers
