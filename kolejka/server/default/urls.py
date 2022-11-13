# vim:ts=4:sts=4:sw=4:expandtab

from django.conf import settings

from django.urls import path

from . import views

app_name = 'default'
urlpatterns = [
    path('login/',    views.login),
    path('logout/',   views.logout),
    path('settings/', views.settings),
    path('',          views.index),
]
