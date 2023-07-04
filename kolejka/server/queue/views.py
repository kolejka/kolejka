# vim:ts=4:sts=4:sw=4:expandtab

from django.conf import settings

import json

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import F, Count
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound, HttpResponseNotAllowed
import django.utils.timezone
from django.views.decorators.csrf import ensure_csrf_cookie

from kolejka.common.limits import KolejkaLimits
from kolejka.common.parse import parse_time
from kolejka.server.response import OKResponse, FAILResponse
from kolejka.server.task.models import Task, Result

@transaction.atomic
def dequeue(request):
    if not request.user.has_perm('task.process_task'):
        return HttpResponseForbidden()
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    content_type = ContentType.objects.get_for_model(Task)
    tasks = list()
    params = json.loads(str(request.read(), request.encoding or 'utf-8'))
    concurency = params.get('concurency', 1)
    limits = KolejkaLimits()
    limits.load(params.get('limits', dict()))
    tags = set(params.get('tags', list()))
    resources = KolejkaLimits()
    resources.copy(limits)
    image_usage = dict()

    available_tasks = Task.objects.filter(assignee__isnull=True).order_by('time_create')[0:100]
    for t in available_tasks:
        if len(tasks) > concurency:
            break
        tt = t.task()
        if len(tasks) > 0 and tt.exclusive:
            continue
        if not set(tt.requires).issubset(tags):
            continue
        if resources.cpus is not None and (tt.limits.cpus is None or tt.limits.cpus > resources.cpus):
            continue
        if tt.limits.gpus is not None and tt.limits.gpus > 0:
            if resources.gpus is None or tt.limits.gpus > resources.gpus:
                continue
            if resources.gpu_memory is not None and (tt.limits.gpu_memory is None or tt.limits.gpu_memory > resources.gpu_memory):
                continue
        if resources.memory is not None and (tt.limits.memory is None or tt.limits.memory > resources.memory):
            continue
        if resources.swap is not None and (tt.limits.swap is None or tt.limits.swap > resources.swap):
            continue
        if resources.pids is not None and (tt.limits.pids is None or tt.limits.pids > resources.pids):
            continue
        if resources.storage is not None and (tt.limits.storage is None or tt.limits.storage > resources.storage):
            continue
        if resources.image is not None:
            if tt.limits.image is None:
                continue
            image_usage_add = max(image_usage.get(tt.image, 0), tt.limits.image) - image_usage.get(tt.image, 0)
            if image_usage_add > resources.image:
                continue
        if resources.workspace is not None and (tt.limits.workspace is None or tt.limits.workspace > resources.workspace):
            continue
        if resources.network is not None and (tt.limits.network is None or tt.limits.network and not resources.network):
            continue
        if resources.time is not None and (tt.limits.time is None or tt.limits.time > resources.time):
            continue
        if resources.perf_instructions is not None and (tt.limits.perf_instructions is None or tt.limits.perf_instructions > resources.perf_instructions):
            continue
        if resources.perf_cycles is not None and (tt.limits.perf_cycles is None or tt.limits.perf_cycles > resources.perf_cycles):
            continue
        if resources.cgroup_depth is not None and (tt.limits.cgroup_depth is None or tt.limits.cgroup_depth > resources.cgroup_depth):
            continue
        if resources.cgroup_descendants is not None and (tt.limits.cgroup_descendants is None or tt.limits.cgroup_descendants > resources.cgroup_descendants):
            continue

        tasks.append(tt.dump())
        t.assignee = request.user
        t.time_assign = django.utils.timezone.now() 
        t.save()
        if resources.cpus is not None:
            resources.cpus -= tt.limits.cpus
        if resources.gpus is not None and tt.limits.gpus is not None:
            resources.gpus -= tt.limits.gpus
        if resources.memory is not None:
            resources.memory -= tt.limits.memory
        if resources.swap is not None:
            resources.swap -= tt.limits.swap
        if resources.pids is not None:
            resources.pids -= tt.limits.pids
        if resources.storage is not None:
            resources.storage -= tt.limits.storage
        if resources.image is not None:
            resources.image -= image_usage_add
            image_usage[tt.image] = max(image_usage.get(tt.image, 0), tt.limits.image)
        if resources.workspace is not None:
            resources.workspace -= tt.limits.workspace
        if resources.perf_instructions is not None:
            resources.perf_instructions -= tt.limits.perf_instructions
        if resources.perf_cycles is not None:
            resources.perf_cycles -= tt.limits.perf_cycles
        if resources.cgroup_descendants is not None:
            resources.cgroup_descendants -= tt.limits.cgroup_descendants
        if tt.exclusive:
            break

    response = dict()
    response['tasks'] = tasks
    return OKResponse(response)

def stats(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    response = dict()
    response['task_count'] = Task.objects.count()
    response['task_resolved_count'] = Task.objects.filter(result__isnull=False).count()
    response['task_unresolved_count'] = Task.objects.filter(result__isnull=True).count()
    response['task_unassigned_count'] = Task.objects.filter(assignee__isnull=True).count()
    assignees = dict([ (v['assignee_username'], v['task_count']) for v in Task.objects.filter(assignee__isnull=False, result__isnull=True).annotate(assignee_username=F('assignee__username')).values('assignee_username').annotate(task_count=Count('assignee_username')) ])
    response['task_assigned_count'] = sum(assignees.values())
    response['task_assignees'] = assignees
    return OKResponse(response)
