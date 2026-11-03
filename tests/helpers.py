import importlib
from contextlib import contextmanager

from django.conf import settings
from django.test import override_settings

from django_simple_third_party_jwt import settings as jwt_settings


@contextmanager
def package_settings(remove=(), **overrides):
    """The package reads its settings once, at import. Reload them with some Django
    settings removed or overridden, then reload them again with the test settings so
    other tests are not affected."""
    try:
        with override_settings(**overrides):
            for name in remove:
                delattr(settings, name)
            yield importlib.reload(jwt_settings)
    finally:
        importlib.reload(jwt_settings)
