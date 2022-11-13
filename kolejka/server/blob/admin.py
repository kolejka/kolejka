# vim:ts=4:sts=4:sw=4:expandtab

from django.conf import settings

from django.contrib import admin

from . import models

@admin.register(models.Blob)
class BlobAdmin(admin.ModelAdmin):
    pass

@admin.register(models.Reference)
class ReferenceAdmin(admin.ModelAdmin):
    pass
