"""
WSGI config for forest_biodiversity_tracker project.
Entry point for production WSGI servers like Gunicorn, uWSGI, or Apache mod_wsgi.
"""

import os
import sys
from django.core.wsgi import get_wsgi_application

# Add the project directory to the Python path
# This is useful for production deployments
path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path not in sys.path:
    sys.path.append(path)

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forest_tracker.settings')

# Create the WSGI application
application = get_wsgi_application()

# Optional: Add monitoring middleware for production
# from monitoring.middleware import MonitoringMiddleware
# application = MonitoringMiddleware(application)

# Optional: For using whitenoise to serve static files in production
# from whitenoise import WhiteNoise
# from django.conf import settings
# application = WhiteNoise(application, root=settings.STATIC_ROOT)