from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BiodiversityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'biodiversity'
    verbose_name = _('Biodiversity Tracking System')

    def ready(self):
        """
        Runs when Django starts.
        Keep lightweight — avoid DB queries or heavy logic here.
        """
        # Optional startup message (safe for development)
        import sys
        if 'runserver' in sys.argv:
            print("✓ Biodiversity Tracking app is ready")