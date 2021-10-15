# vim:ts=4:sts=4:sw=4:expandtab

from django.urls import path

from . import views

app_name = 'task'
urlpatterns = [
    path('task/', views.task),
    path('task/<key>/', views.task),
    path('result/', views.result),
    path('result/<key>/', views.result),
]
