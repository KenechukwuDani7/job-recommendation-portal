"""Serverless entry point.

The platform imports ``app`` from this module and calls it as a WSGI
application. The project root is put on the import path first, because the
function runs with this file's directory as the working directory rather than
the repository root.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()
application = app
