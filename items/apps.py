from django.apps import AppConfig

class ItensConfig(AppConfig):
    name = 'items'

    def ready(self):
        import items.signals


class ItemsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'items'
