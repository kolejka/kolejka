# vim:ts=4:sts=4:sw=4:expandtab

import hashlib
import os

from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from . import models

READ_BUF_SIZE = 8192

def reference(request, key):
    if request.method == 'POST':
        if key != '':
            return HttpResponseForbidden()
        if not request.user.is_authenticated():
            return HttpResponseForbidden()
        hasher = hashlib.new(settings.BLOB_HASH_ALGORITHM)
        temp_file = models.Blob.blob_temp_path()
        file_size = 0
        blob = None
        try:
            with open(temp_file, 'wb') as tf:
                while True:
                    buf = request.read(READ_BUF_SIZE)
                    if len(buf) == 0 :
                        break
                    file_size += len(buf)
                    tf.write(buf)
                    hasher.update(buf)
            key = hasher.hexdigest()
            blob, created = models.Blob.objects.get_or_create(key=key, size=file_size)
            if not os.path.exists(blob.store_path):
                os.rename(temp_file, blob.store_path)
            blob.activate()
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        reference = models.Reference(blob=blob, user=request.user)
        reference.save()
        response = dict()
        response['reference'] = {
            'key' : reference.key,
            'blob' : reference.blob.key,
            'size' : reference.blob.size,
            'time_create' : reference.time_create,
            'time_access' : reference.time_access,
        }
        return JsonResponse(response)
    try:
        reference = models.Reference.objects.get(key=key)
    except models.Reference.DoesNotExist:
        return HttpResponseNotFound()
    if not reference.public:
        if not request.user.is_authenticated():
            return HttpResponseForbidden()
        if not request.user.is_superuser and request.user != reference.user:
            return HttpResponseForbidden()
    if request.method == 'PUT':
        response = dict()
        response['reference'] = {
            'key' : reference.key,
            'blob' : reference.blob.key,
            'size' : reference.blob.size,
            'time_create' : reference.time_create,
            'time_access' : reference.time_access,
        }
        return JsonResponse(response)
    if request.method == 'DELETE':
        if not request.user.is_authenticated():
            return HttpResponseForbidden()
        if not request.user.is_superuser and request.user != reference.user:
            return HttpResponseForbidden()
        reference.delete()
        return JsonResponse({'deleted' : True})
    if request.method == 'GET' or request.method == 'HEAD':
        reference.blob.save()
        reference.save()
        return StreamingHttpResponse(reference.blob.open(), content_type='application/octet-stream')

def blob(request, key):
    try:
        blob = models.Blob.objects.get(key = key)
    except models.Blob.DoesNotExist:
        return HttpResponseNotFound()
    if request.method == 'POST':
        if not request.user.is_authenticated():
            return HttpResponseForbidden()
        reference = models.Reference(
                user = request.user,
                blob = blob
        )
        reference.save()
        blob.save()
        response = dict()
        response['reference'] = {
            'key' : reference.key,
            'blob' : reference.blob.key,
            'size' : reference.blob.size,
            'time_create' : reference.time_create,
            'time_access' : reference.time_access,
        }
        return JsonResponse(response)
    if request.method == 'POST':
        response = dict()
        response['blob'] = {
            'key' : blob.key,
            'size' : blob.size,
            'time_create' : blob.time_create,
            'time_access' : blob.time_access,
            'references' : blob.reference_set.count(),
        }
        return JsonResponse(response)
    if request.method == 'DELETE':
        if not request.user.is_superuser:
            return HttpResponseForbidden()
        blob.reference_set.all().delete()
        blob.delete()
        return JsonResponse({'deleted' : True})
    if request.method == 'GET' or request.method == 'HEAD':
        if not request.user.is_superuser:
            return HttpResponseForbidden()
        blob.save()
        return StreamingHttpResponse(blob.open(), content_type='application/octet-stream')
