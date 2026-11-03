"""The test settings with a custom user model, and the real migration files of every app."""
from tests.settings import *  # noqa: F401,F403
from tests.settings import INSTALLED_APPS

INSTALLED_APPS = INSTALLED_APPS + ["tests.custom_user"]
AUTH_USER_MODEL = "custom_user.EmailUser"

# Apply the migrations that ship with the package (and the test app), instead of creating
# the tables straight from the models as tests/settings.py does.
MIGRATION_MODULES = {}
