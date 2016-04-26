from django.apps import AppConfig


class OrchestraAppConfig(AppConfig):
    name = 'orchestra'
    verbose_name = 'Orchestra'

    def ready(self):
        from orchestra.accounts import signals  # noqa
