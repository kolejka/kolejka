# vim:ts=4:sts=4:sw=4:expandtab

import os

KOLEJKA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(KOLEJKA_DIR)

SECRET_KEY = '__CHANGE_THIS_VALUE__'

DEBUG = False

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'kolejka.server.blob',
    'kolejka.server.task',
    'kolejka.server.queue',
    'kolejka.server.default',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

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


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(PROJECT_DIR, '../kolejka-server-static')

LOGIN_REDIRECT_URL = '/'

BLOB_HASH_ALGORITHM = 'sha256'
BLOB_STORE_PATH = os.path.join(PROJECT_DIR, '../kolejka-server-blobs')

LIMIT_CPUS = None
LIMIT_MEMORY = None
LIMIT_SWAP = None
LIMIT_PIDS = None
LIMIT_STORAGE = None 
LIMIT_NETWORK = None
LIMIT_TIME = None
LIMIT_IMAGE = None
LIMIT_WORKSPACE = None

IMAGE_NAME_MAPS = [
#        ( r'kolejka([:/].*)', r'kolejka\1' ),
]

LIMIT_IMAGE_NAME = [
        r'.*',
#        r'kolejka[:/].*',
]

LOCAL_IMAGE_NAMES = [
#        r'kolejka[:/].*',
]

IMAGE_REGISTRY = None
IMAGE_REGISTRY_NAME = 'kolejka_task'
IMAGE_REGISTRY_USERNAME = None
IMAGE_REGISTRY_PASSWORD = None

try:
    from kolejka.server.settings_local import *
except ImportError:
    pass
