"""The package with a custom user model, run in a separate pytest process.

AUTH_USER_MODEL is fixed once Django starts, so tests/custom_user/flows.py gets its own
process with DJANGO_SETTINGS_MODULE=tests.custom_user.settings. Every other test runs with
Django's built-in User.
"""
import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]


class CustomUserModelRunTests(SimpleTestCase):
    def test_the_package_works_with_a_custom_user_model(self):
        env = dict(os.environ, DJANGO_SETTINGS_MODULE="tests.custom_user.settings")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/custom_user/flows.py"],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout[-4000:] + result.stderr[-2000:])
        self.assertIn("passed", result.stdout)
