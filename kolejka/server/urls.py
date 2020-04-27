# vim:ts=4:sts=4:sw=4:expandtab

from django.conf.urls import include, url
from django.urls import path
from django.contrib.admin import site as admin_site

from .default import urls as default_urls
from .blob import urls as blob_urls
from .task import urls as task_urls
from .queue import urls as queue_urls

urlpatterns = [
    path('admin/', admin_site.urls),
    path('blob/',  include(blob_urls)),
    path('task/',  include(task_urls)),
    path('queue/', include(queue_urls)),
    path('',       include(default_urls)),
]
