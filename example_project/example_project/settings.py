"""
Django settings for example_project project.

Generated by 'django-admin startproject' using Django 1.9.5.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os
import sys
from .orchestra_settings import setup_orchestra


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add local orchestra to the system path: only for testing
sys.path.append(os.path.join(BASE_DIR, '../'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'CHANGEMEOMG'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Application definition
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django_gulp',
    'django.contrib.staticfiles',
    'kronos',
)

# django-gulp settings
GULP_PRODUCTION_COMMAND = 'gulp --gulpfile ../gulpfile.js build --production'  # noqa
# If you need the scss source maps, remove the --production flag
GULP_DEVELOP_COMMAND = 'gulp --gulpfile ../gulpfile.js --production'

# Installed orchestra workflows to be included as Django apps
ORCHESTRA_WORKFLOWS = (
    'simple_workflow',
    'journalism_workflow',
)
INSTALLED_APPS += ORCHESTRA_WORKFLOWS

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'example_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                # Allows access to request object in templates; currently used
                # for displaying hijack notification
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'example_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'orchestra.sqlite3',
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = 'staticfiles'


TESTING = sys.argv[1:2] == ['test']
if TESTING:
    PASSWORD_HASHERS = ('django.contrib.auth.hashers.MD5PasswordHasher',)

setup_orchestra(__name__)
