# vim:ts=4:sts=4:sw=4:expandtab

from django.contrib import admin

from .models import *

@admin.register(Blob)
class BlobAdmin(admin.ModelAdmin):
    pass

@admin.register(Reference)
class ReferenceAdmin(admin.ModelAdmin):
    pass
