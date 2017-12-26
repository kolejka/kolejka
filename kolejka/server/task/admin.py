# vim:ts=4:sts=4:sw=4:expandtab

from django.contrib import admin

from .models import *


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    pass

@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    pass
