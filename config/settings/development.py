"""
Development settings
"""
from .base import *

# Debug
DEBUG = True

# Allowed hosts for development
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Database configuration is inherited from base.py (PostgreSQL)

# Development-specific apps
INSTALLED_APPS += [
    'debug_toolbar',
]

# Development-specific middleware
MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# Debug Toolbar
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

# Debug Toolbar configuration
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
}

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable HTTPS redirects in development
SECURE_SSL_REDIRECT = False

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Additional settings for development
CELERY_TASK_ALWAYS_EAGER = False  # Set to True to run tasks synchronously for debugging
CELERY_TASK_EAGER_PROPAGATES = True
