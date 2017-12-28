# vim:ts=4:sts=4:sw=4:expandtab

import json

import django.conf
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound, HttpResponseNotAllowed
from django.views.decorators.csrf import ensure_csrf_cookie

from kolejka.common import KolejkaLimits
from kolejka.server.task.models import Task

def dequeue(request):
    if request.method == 'POST':
        if not request.user.is_authenticated():
            return HttpResponseForbidden()
#TODO: Check that user can get tasks
        tasks = list()
        params = json.loads(str(request.read(), request.encoding or 'utf-8')) 
        concurency = params.get('concurency', 1)
        limits = KolejkaLimits()
        limits.load(params.get('limits', {}))

        available_tasks = Task.objects.filter(assignee=None).order_by('time_create')[0:100]
        for t in available_tasks:
            if True:
                tasks.append(t.task().dump())
                t.assignee = request.user
                t.save()
                break

        response = dict()
        response['tasks'] = tasks
        return JsonResponse(response)
    return HttpResponseNotAllowed(['POST'])
