# vim:ts=4:sts=4:sw=4:expandtab

from django.conf.urls import url
from django.urls import path

from . import views

app_name = 'blob'
urlpatterns = [
    path('blob/<key>/', views.blob),
    path('reference/', views.reference),
    path('reference/<key>/', views.reference),
]
