#!/usr/bin/env python3
# vim:ts=4:sts=4:sw=4:expandtab

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kolejka.server.settings")

application = get_wsgi_application()
