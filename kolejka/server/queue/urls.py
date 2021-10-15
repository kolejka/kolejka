# vim:ts=4:sts=4:sw=4:expandtab

from django.urls import path

from . import views

app_name = 'queue'
urlpatterns = [
    path('dequeue/', views.dequeue),
    path('stats/', views.stats),
]
