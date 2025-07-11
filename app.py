import os
import django
from django.conf import settings


class StreamlitDjangoApp:
    def __init__(self):
        self._models_cached = None
        self._setup_django()

    def _setup_django(self):
        """Configure Django if not already configured."""
        if not settings.configured:
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
            django.setup()

    def get_models(self):
        """Get Django models with caching."""
        if self._models_cached is None:
            from core.base.models import (
                Transaction,
                Category,
                Subcategory,
                BankAccount,
                Tag,
            )

            self._models_cached = {
                "Transaction": Transaction,
                "Category": Category,
                "Subcategory": Subcategory,
                "BankAccount": BankAccount,
                "Tag": Tag,
            }
        return self._models_cached


# Global app instance
app_launcher = StreamlitDjangoApp()
