# vim:ts=4:sts=4:sw=4:expandtab

import json
import uuid

from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound, HttpResponseNotAllowed, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from kolejka.common import KolejkaTask, KolejkaResult, KolejkaLimits
from kolejka.server.blob.models import Reference

from . import models

def task(request, key):
    if request.method == 'POST':
        if key != '':
            return HttpResponseForbidden()
        if not request.user.is_authenticated():
            return HttpResponseForbidden()
        t = KolejkaTask(None)
        t.load(request.read())
        t.id = uuid.uuid4().hex
        for k,f in t.files.items():
            if not f.reference:
                return HttpResponseForbidden()
            f.path = None
        refs = list()
        for k,f in t.files.items():
            ref = Reference.objects.get(key = f.reference)
            if not ref.public:
                if not request.user.is_superuser and request.user != ref.user:
                    return HttpResponseForbidden()
            refs.append(ref)
        limits = KolejkaLimits(
                cpus=settings.LIMIT_CPUS,
                memory=settings.LIMIT_MEMORY,
                pids=settings.LIMIT_PIDS,
                storage=settings.LIMIT_STORAGE,
                network=settings.LIMIT_NETWORK,
                time=settings.LIMIT_TIME,
            )
        t.limits.update(limits)

        task = models.Task(user=request.user, key=t.id, description=json.dumps(t.dump()))
        task.save()
        for ref in refs:
            task.files.add(ref)
        response = dict()
        response['task'] = task.task().dump()
        return JsonResponse(response)
    try:
        task = models.Task.objects.get(key=key)
    except models.Task.DoesNotExist:
        return HttpResponseNotFound()
    if not request.user.is_authenticated():
        return HttpResponseForbidden()
    if not request.user.is_superuser and request.user != task.user and request.user != task.assignee:
        return HttpResponseForbidden()
    if request.method == 'PUT':
        response = dict()
        response['task'] = task.task().dump()
        return JsonResponse(response)
    if request.method == 'DELETE':
        task.delete()
        return JsonResponse({'deleted' : True})
    if request.method == 'GET' or request.method == 'HEAD':
        response = dict()
        response['task'] = task.task().dump()
        return JsonResponse(response)
    return HttpResponseNotAllowed(['HEAD', 'GET', 'POST', 'PUT', 'HEAD'])

def result(request, key):
    if request.method == 'POST':
        if key != '':
            return HttpResponseForbidden()
        if not request.user.is_authenticated():
            return HttpResponseForbidden()
        r = KolejkaResult(None)
        r.load(request.read())
        try:
            task = models.Task.objects.get(key = r.id)
        except models.Task.DoesNotExist:
            return HttpResponseForbidden()
        if not request.user.is_superuser and request.user != task.user and request.user != task.assignee:
            return HttpResponseForbidden()
        for k,f in r.files.items():
            if not f.reference:
                return HttpResponseForbidden()
            f.path = None
        refs = list()
        for k,f in r.files.items():
            ref = Reference.objects.get(key = f.reference)
            if not ref.public:
                if not request.user.is_superuser and request.user != ref.user:
                    return HttpResponseForbidden()
            refs.append(ref)
        result,created = models.Result.objects.get_or_create(task=task, user=request.user, description=json.dumps(r.dump()))
        result.save()
        for ref in refs:
            result.files.add(ref)
        response = dict()
        response['result'] = result.result().dump()
        return JsonResponse(response)
    try:
        task = models.Task.objects.get(key=key)
        result = models.Result.objects.get(task=task)
    except models.Task.DoesNotExist:
        return HttpResponseNotFound()
    except models.Result.DoesNotExist:
        return HttpResponseNotFound()
    if not request.user.is_authenticated():
        return HttpResponseForbidden()
    if not request.user.is_superuser and request.user != task.user and request.user != task.assignee:
        return HttpResponseForbidden()
    if request.method == 'PUT':
        response = dict()
        response['result'] = result.result().dump()
        return JsonResponse(response)
    if request.method == 'DELETE':
        result.delete()
        return JsonResponse({'deleted' : True})
    if request.method == 'GET' or request.method == 'HEAD':
        response = dict()
        response['result'] = result.result().dump()
        return JsonResponse(response)
    return HttpResponseNotAllowed(['HEAD', 'GET', 'POST', 'PUT', 'HEAD'])
