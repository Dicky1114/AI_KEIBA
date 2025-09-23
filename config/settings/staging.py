"""
Staging settings
"""
from .base import *

# Debug
DEBUG = config('DEBUG', default=False, cast=bool)

# Staging-specific settings
ALLOWED_HOSTS = ['staging.keiba-prediction.com', 'localhost']

# Email backend for staging
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Reduced security for staging
SECURE_SSL_REDIRECT = False

# CORS settings for staging
CORS_ALLOW_ALL_ORIGINS = True
