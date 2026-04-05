#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import warnings


def main():
    """Run administrative tasks."""
    # Set the default Django settings module for the 'manage.py' utility
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forest_tracker.settings')
    
    # Suppress deprecation warnings in development (optional)
    if os.environ.get('DJANGO_ENV') == 'development':
        warnings.filterwarnings('ignore', category=DeprecationWarning)
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # Execute the command
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()