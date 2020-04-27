# vim:ts=4:sts=4:sw=4:expandtab

import datetime
import os
import uuid

from django.conf import settings
from django.db import models

from kolejka.common import KolejkaTask, KolejkaResult
from kolejka.server.blob.models import Reference

class Task(models.Model):
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='kolejka_tasks')
    key         = models.CharField(max_length=64, unique=True, null=False)
    description = models.TextField()
    time_create = models.DateTimeField(auto_now_add=True, null=False)
    files       = models.ManyToManyField(Reference)
    assignee    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='kolejka_assignments')
    time_assign = models.DateTimeField(null=True)

    def task(self, task_path=None):
        task = KolejkaTask(task_path)
        task.load(self.description)
        return task

    class Meta:
        permissions = [('process_task', 'Can process task')]


class Result(models.Model):
    task        = models.OneToOneField(Task, on_delete=models.CASCADE)
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='kolejka_results')
    description = models.TextField()
    time_create = models.DateTimeField(auto_now_add=True, null=False)
    files       = models.ManyToManyField(Reference)

    def result(self, result_path=None):
        result = KolejkaResult(result_path)
        result.load(self.description)
        return result

def task_init(instance, **kwargs):
    if not instance.key:
        instance.key = uuid.uuid4().hex

def task_delete(instance, **kwargs):
    if settings.IMAGE_REGISTRY is not None and settings.IMAGE_REGISTRY_NAME is not None:
        image_name = settings.IMAGE_REGISTRY+'/'+settings.IMAGE_REGISTRY_NAME+':'+t.id
        task = instance.task()
        if task.image == image_name:
            pass
            #TODO: remove tag from registry


models.signals.post_init.connect(task_init, Task)
models.signals.post_delete.connect(task_delete, Task)
