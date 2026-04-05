"""
ASGI config for forest_biodiversity_tracker project.
Used for WebSockets, real-time notifications, and async features.
"""

import os
from django.core.asgi import get_asgi_application

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forest_tracker.settings')

# Initialize Django ASGI application
django_asgi_app = get_asgi_application()

# Optional: Add WebSocket/Channels support for real-time alerts
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# from biodiversity import routing

# For now, just use standard ASGI
application = django_asgi_app

# If you want to add WebSocket support for real-time biodiversity alerts:
# application = ProtocolTypeRouter({
#     "http": django_asgi_app,
#     "websocket": AuthMiddlewareStack(
#         URLRouter(
#             routing.websocket_urlpatterns
#         )
#     ),
# })