"""Checks on the README and the example project (no Django requests involved)."""
import re
from pathlib import Path

from django.test import SimpleTestCase

from django_simple_third_party_jwt import settings as jwt_settings

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SETTINGS = ROOT / "src" / "django_simple_third_party_jwt" / "settings.py"


def documentation_files():
    yield ROOT / "README.md"
    yield ROOT / "example" / "django_simple_third_party_jwt_example" / "django_simple_third_party_jwt_example" / "settings.py"
    docs = ROOT / "docs"
    if docs.is_dir():
        yield from (p for p in docs.rglob("*") if p.is_file() and p.suffix in {".md", ".html", ".txt", ".py"})


class NoSecretsInDocsTests(SimpleTestCase):
    def test_built_in_microsoft_secret_is_not_copied_into_docs_or_example(self):
        secret = getattr(jwt_settings, "__DEV_MICROSOFT_CLIENT_SECRET", None)
        if not secret:
            self.skipTest("the package no longer ships a demo secret")
        for path in documentation_files():
            with self.subTest(str(path.relative_to(ROOT))):
                # assertFalse rather than assertNotIn: a failure must not print the value.
                self.assertFalse(secret in path.read_text(encoding="utf-8"),
                                 f"{path.name} contains the package's built-in Microsoft client secret")


class ReadmeSettingsTests(SimpleTestCase):
    def test_every_setting_the_package_reads_is_in_the_readme(self):
        source = PACKAGE_SETTINGS.read_text(encoding="utf-8")
        names = set(re.findall(r'(?:getattr\(\s*settings,\s*|_setting_or_demo\(\s*)"([A-Z0-9_]+)"', source))
        self.assertIn("JWT_3RD_PREFIX", names)
        self.assertGreaterEqual(len(names), 8)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        missing = sorted(name for name in names if f"`{name}`" not in readme)
        self.assertEqual(missing, [], "settings missing from the README's settings reference")
