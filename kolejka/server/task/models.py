# vim:ts=4:sts=4:sw=4:expandtab

import datetime
import os
import uuid

from django.conf import settings
from django.db import models

from kolejka.server.blob.models import Reference

class Task(models.Model):
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    key         = models.CharField(max_length=64, unique=True, null=False)
    description = models.TextField()
    time_create = models.DateTimeField(auto_now_add=True, null=False)
    files       = models.ManyToManyField(Reference)

class Result(models.Model):
    task        = models.ForeignKey(Task, on_delete=models.CASCADE)
    worker      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL)
    description = models.TextField()
    time_create = models.DateTimeField(auto_now_add=True, null=False)
    files       = models.ManyToManyField(Reference)

def task_init(instance, **kwargs):
    if not instance.key:
        instance.key = uuid.uuid4().hex

models.signals.post_init.connect(task_init, Task)
