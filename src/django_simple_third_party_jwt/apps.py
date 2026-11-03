from django.apps import AppConfig


class DjangoSimpleThirdPartyJWTConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_simple_third_party_jwt'

    def ready(self) -> None:
        from django_simple_third_party_jwt import checks  # noqa: F401  (registers the start-up checks)
