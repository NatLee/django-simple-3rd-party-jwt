"""Checks on the README (no Django requests involved)."""
import re
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SETTINGS = ROOT / "src" / "django_simple_third_party_jwt" / "settings.py"


class ReadmeSettingsTests(SimpleTestCase):
    def test_every_setting_the_package_reads_is_in_the_readme(self):
        source = PACKAGE_SETTINGS.read_text(encoding="utf-8")
        names = set(re.findall(r'(?:getattr\(\s*settings,\s*|_setting_or_demo\(\s*)"([A-Z0-9_]+)"', source))
        self.assertIn("JWT_3RD_PREFIX", names)
        self.assertGreaterEqual(len(names), 8)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        missing = sorted(name for name in names if f"`{name}`" not in readme)
        self.assertEqual(missing, [], "settings missing from the README's settings reference")
