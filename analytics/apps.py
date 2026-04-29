from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'
    verbose_name = "Result Analytics Suite"

    def ready(self):
        # Import signals (important if you add auto logic later)
        pass