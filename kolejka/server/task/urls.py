# vim:ts=4:sts=4:sw=4:expandtab

from django.conf.urls import url

from . import views

app_name = 'task'
urlpatterns = [
    url(r'^(?P<key>[0-9a-f]*)/?$', views.task),
    url(r'^(?P<key>[0-9a-f]*)/result/?$', views.result),
]
