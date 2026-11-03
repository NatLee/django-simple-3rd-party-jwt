import os
import django
from django.conf import settings
from django.core.management import call_command
from django.test.utils import setup_test_environment

# 設置 DJANGO_SETTINGS_MODULE 環境變量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')

# 初始化 Django
django.setup()

# Same set-up as Django's own test runner, so tests can inspect
# response.context and the templates that were rendered.
setup_test_environment()

# 建立資料庫
call_command('migrate', '--run-syncdb', verbosity=0, interactive=False)