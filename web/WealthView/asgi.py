"""
ASGI entrypoint. Configures Django and then runs the application
defined in the ASGI_APPLICATION setting.
"""

import os
import django
from django.core.asgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "WealthView.settings")

django.setup()
application = get_default_application()