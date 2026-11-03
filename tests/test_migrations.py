from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings


class MigrationTests(TestCase):
    # tests/settings.py turns migrations off to speed up the other tests;
    # here we need the real migration files that ship with the package.
    @override_settings(MIGRATION_MODULES={})
    def test_models_match_shipped_migrations(self):
        """Every model change ships with a migration, so users never have to run
        makemigrations for this app (which would write into site-packages)."""
        out = StringIO()
        try:
            call_command(
                "makemigrations",
                "django_simple_third_party_jwt",
                check=True,
                dry_run=True,
                stdout=out,
                stderr=StringIO(),
            )
        except SystemExit:
            self.fail("Model changes without a migration:\n" + out.getvalue())
