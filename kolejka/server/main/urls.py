# vim:ts=4:sts=4:sw=4:expandtab

from django.conf.urls import url

from . import views

app_name = 'main'
urlpatterns = [
    url(r'settings/?$', views.settings),
    url(r'', views.index),
]
