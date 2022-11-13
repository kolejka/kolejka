#!/usr/bin/env python3
# vim:ts=4:sts=4:sw=4:expandtab

from kolejka.server import settings

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kolejka.server.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
