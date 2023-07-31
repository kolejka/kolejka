# vim:ts=4:sts=4:sw=4:expandtab

from django.conf import settings

import json
import logging
import re
import subprocess
import threading
import urllib.parse
import urllib.request
import uuid

from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotFound, HttpResponseNotAllowed, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from kolejka.common.limits import KolejkaLimits
from kolejka.common.task import KolejkaTask, KolejkaResult
from kolejka.server.blob.models import Reference
from kolejka.server.response import OKResponse, FAILResponse

from . import models

def task(request, key=''):
    if request.method == 'POST':
        if key != '':
            return HttpResponseForbidden()
        if not request.user.has_perm('task.add_task'):
            return HttpResponseForbidden()
        t = KolejkaTask(None)
        t.load(request.read())
        for image_re, image_sub in settings.IMAGE_NAME_MAPS:
            t.image = re.sub(r'^'+image_re+r'$', image_sub, t.image)
        accept_image = False
        for image_re in settings.LIMIT_IMAGE_NAME:
            if re.match(image_re, t.image):
                accept_image = True
                break
        if not accept_image:
            return FAILResponse(message=f'Image {t.image} is not accepted by the server')
        local_image = False
        for image_re in settings.LOCAL_IMAGE_NAMES:
            if re.match(image_re, t.image):
                local_image = True
                break
        t.id = uuid.uuid4().hex
        for k,f in t.files.items():
            if not f.reference:
                return FAILResponse(message=f'File {k} does not have a reference')
            f.path = None
        refs = list()
        for k,f in t.files.items():
            try:
                ref = Reference.objects.get(key = f.reference)
            except Reference.DoesNotExist:
                return FAILResponse(message=f'Reference for file {k} is unknown')
            if not ref.public:
                if not request.user.has_perm('blob.view_reference') and request.user != ref.user:
                    return FAILResponse(message=f'Reference for file {k} is unknown')
            refs.append(ref)
        limits = KolejkaLimits(
                cpus=settings.LIMIT_CPUS,
                memory=settings.LIMIT_MEMORY,
                swap=settings.LIMIT_SWAP,
                pids=settings.LIMIT_PIDS,
                storage=settings.LIMIT_STORAGE,
                network=settings.LIMIT_NETWORK,
                time=settings.LIMIT_TIME,
                image=settings.LIMIT_IMAGE,
                workspace=settings.LIMIT_WORKSPACE,
                gpus=settings.LIMIT_GPUS,
                gpu_memory=settings.LIMIT_GPU_MEMORY,
                perf_instructions=settings.LIMIT_PERF_INSTRUCTIONS,
                perf_cycles=settings.LIMIT_PERF_CYCLES,
                cgroup_depth=settings.LIMIT_CGROUP_DEPTH,
                cgroup_descendants=settings.LIMIT_CGROUP_DESCENDANTS,
            )
        t.limits.update(limits)


        if settings.IMAGE_REGISTRY is not None and settings.IMAGE_REGISTRY_NAME is not None and not local_image:
            try:
                subprocess.run(['docker', 'pull', t.image], check=True)
                docker_inspect_run = subprocess.run(['docker', 'image', 'inspect', '--format', '{{json .Id}}', t.image], stdout=subprocess.PIPE, check=True)
                image_id = str(json.loads(str(docker_inspect_run.stdout, 'utf-8'))).split(':')[-1]
                logging.info(image_id)
                docker_inspect_run = subprocess.run(['docker', 'image', 'inspect', '--format', '{{json .Size}}', t.image], stdout=subprocess.PIPE, check=True)
                image_size = int(json.loads(str(docker_inspect_run.stdout, 'utf-8')))
            except:
                return FAILResponse(message=f'Image {t.image} could not be pulled')
            if t.limits.image is not None and image_size > t.limits.image:
                return FAILResponse(message=f'Image {t.image} exceeds image size limit {t.limits.image}')
            image_name = settings.IMAGE_REGISTRY+'/'+settings.IMAGE_REGISTRY_NAME+':'+image_id
            try:
                subprocess.run(['docker', 'tag', t.image, image_name], check=True)
                subprocess.run(['docker', 'push', image_name], check=True)
                subprocess.run(['docker', 'rmi', image_name], check=True)
            except:
                return FAILResponse(message=f'Image {t.image} could not be pushed to local repository')
            t.image = image_name
            t.limits.image = image_size

        task = models.Task(user=request.user, key=t.id, description=json.dumps(t.dump()))
        task.save()
        for ref in refs:
            task.files.add(ref)
        response = dict()
        response['task'] = task.task().dump()
        return OKResponse(response)
    if not request.user.is_authenticated:
        return HttpResponseForbidden()
    try:
        task = models.Task.objects.get(key=key)
    except models.Task.DoesNotExist:
        return HttpResponseNotFound()
    if not request.user.has_perm('task.view_task') and request.user != task.user and request.user != task.assignee:
        return HttpResponseForbidden()
    if request.method == 'PUT':
        response = dict()
        response['task'] = task.task().dump()
        return OKResponse(response)
    if request.method == 'DELETE':
        if not request.user.has_perm('task.delete_task') and request.user != task.user:
            return HttpResponseForbidden()
        task.delete()
        return OKResponse(deleted=True)
    if request.method == 'GET' or request.method == 'HEAD':
        response = dict()
        response['task'] = task.task().dump()
        return OKResponse(response)
    return HttpResponseNotAllowed(['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

def result_callback(result):
    url = result.task.task().callback_url
    if url:
        try:
            parsed_url = urllib.parse.urlparse(url)
            if parsed_url.scheme not in [ 'http', 'https' ] or parsed_url.hostname not in settings.ALLOWED_CALLBACK_HOSTS:
                logging.warning(f'Callback \'{url}\' is not allowed')
                return
        except:
            logging.warning(f'Callback \'{url}\' is malformed')
            return
        headers = dict()
        headers['User-Agent'] = settings.CALLBACK_USER_AGENT
        headers['Content-Type'] = 'application/json'
        response = dict()
        response['task'] = result.task.task().dump()
        response['result'] = result.result().dump()
        data = bytes(json.dumps(response), 'utf-8')
        request = urllib.request.Request(url=url, data=data, headers=headers, method='POST')
        def opener(request):
            try:
                response = urllib.request.urlopen(request)
            except:
                logging.warning(f'Callback \'{url}\' failed')
                pass
        threading.Thread(target=opener, args=[request]).run()

def result(request, key=''):
    if request.method == 'POST':
        if key != '':
            return HttpResponseForbidden()
        if not request.user.has_perm('task.process_task'):
            return HttpResponseForbidden()
        r = KolejkaResult(None)
        r.load(request.read())
        try:
            task = models.Task.objects.get(key = r.id)
        except models.Task.DoesNotExist:
            return HttpResponseForbidden()
        if not request.user.has_perm('task.add_result') and request.user != task.assignee:
            return HttpResponseForbidden()
        for k,f in r.files.items():
            if not f.reference:
                return FAILResponse(message=f'File {k} does not have a reference')
            f.path = None
        refs = list()
        for k,f in r.files.items():
            try:
                ref = Reference.objects.get(key = f.reference)
            except Reference.DoesNotExist:
                return FAILResponse(message=f'Reference for file {k} is unknown')
            if not ref.public:
                if request.user != ref.user:
                    return FAILResponse(message=f'Reference for file {k} belongs to a different user')
            refs.append(ref)
        result,created = models.Result.objects.get_or_create(task=task, user=request.user, description=json.dumps(r.dump()))
        result.save()
        for ref in refs:
            ref.user = task.user
            ref.save()
            result.files.add(ref)
        response = dict()
        response['result'] = result.result().dump()
        result_callback(result)
        return OKResponse(response)
    if not request.user.is_authenticated:
        return HttpResponseForbidden()
    try:
        task = models.Task.objects.get(key=key)
        result = models.Result.objects.get(task=task)
    except models.Task.DoesNotExist:
        return FAILResponse(message=f'Task {key} is unknown')
    except models.Result.DoesNotExist:
        return HttpResponseNotFound()
    if not request.user.has_perm('task.view_result') and request.user != task.user:
        return HttpResponseForbidden()
    if request.method == 'PUT':
        response = dict()
        response['result'] = result.result().dump()
        return OKResponse(response)
    if request.method == 'DELETE':
        if not request.user.has_perm('task.delete_result') and request.user != task.user:
            return HttpResponseForbidden()
        result.delete()
        return OKResponse(deleted=True)
    if request.method == 'GET' or request.method == 'HEAD':
        response = dict()
        response['result'] = result.result().dump()
        return OKResponse(response)
    return HttpResponseNotAllowed(['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])
