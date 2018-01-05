# vim:ts=4:sts=4:sw=4:expandtab

import os

KOLEJKA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(KOLEJKA_DIR)

SECRET_KEY = '__CHANGE_THIS_VALUE__'

DEBUG = False

ALLOWED_HOSTS = [
    'localhost',
]

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'kolejka.server.blob',
    'kolejka.server.task',
    'kolejka.server.queue',
    'kolejka.server.main',
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

ROOT_URLCONF = 'kolejka.server.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(KOLEJKA_DIR, 'server/templates')
            ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'kolejka.server.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_DIR, '../kolejka-server-database.sqlite3')
    }
}

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(PROJECT_DIR, '../kolejka-server-static')

BLOB_HASH_ALGORITHM = 'sha256'
BLOB_STORE_PATH = os.path.join(PROJECT_DIR, '../kolejka-server-blobs')

LIMIT_CPUS = None
LIMIT_MEMORY = None
LIMIT_PIDS = None
LIMIT_STORAGE = None 
LIMIT_NETWORK = None
LIMIT_TIME = None

try:
    from kolejka.server.settings_local import *
except ImportError:
    pass
