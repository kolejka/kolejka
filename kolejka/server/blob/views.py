# vim:ts=4:sts=4:sw=4:expandtab

import hashlib
import os

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotFound, FileResponse
from django.views.decorators.csrf import csrf_exempt

from . import models

from kolejka.server.response import OKResponse, FAILResponse

READ_BUF_SIZE = 8192

def reference(request, key=''):
    if request.method == 'POST': #CREATE A NEW REFERENCE BY SENDING A BLOB
        if key != '':
            return HttpResponseForbidden()
        if not request.user.has_perm('blob.add_reference'):
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
        return OKResponse(response)
    try:
        reference = models.Reference.objects.get(key=key)
    except models.Reference.DoesNotExist:
        return HttpResponseNotFound()
    if not reference.public and request.user != reference.user:
        if not request.user.has_perm('blob.view_reference'): 
            return HttpResponseForbidden()
    if request.method == 'PUT': #QUERY REFERENCE DATA
        response = dict()
        response['reference'] = {
            'key' : reference.key,
            'blob' : reference.blob.key,
            'size' : reference.blob.size,
            'time_create' : reference.time_create,
            'time_access' : reference.time_access,
        }
        return OKResponse(response)
    if request.method == 'DELETE': #DELETE REFERENCE
        if not request.user.has_perm('blob.delete_reference') and request.user != reference.user:
            return HttpResponseForbidden()
        reference.delete()
        return OKResponse({'deleted' : True})
    if request.method == 'GET' or request.method == 'HEAD': #GET REFERENCED BLOB
        reference.blob.save()
        reference.save()
        if settings.USE_X_SENDFILE:
            return HttpResponse(headers={'X-Sendfile': reference.blob.realpath}, content_type='application/octet-stream')
        return FileResponse(reference.blob.open(), content_type='application/octet-stream')
    return HttpResponseNotAllowed(['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

def blob(request, key):
    try:
        blob = models.Blob.objects.get(key = key)
    except models.Blob.DoesNotExist:
        return HttpResponseNotFound()
    if not request.user.has_perm('blob.view_blob'):
        return HttpResponseForbidden()
    if request.method == 'POST': #CREATE NEW REFERENCE TO THE BLOB
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
        return OKResponse(response)
    if request.method == 'PUT': #QUERY BLOB DATA
        response = dict()
        response['blob'] = {
            'key' : blob.key,
            'size' : blob.size,
            'time_create' : blob.time_create,
            'time_access' : blob.time_access,
            'references' : blob.reference_set.count(),
        }
        return OKResponse(response)
    if request.method == 'DELETE': #DELETE BLOB AND ALL REFERENCES
        if not request.user.has_perm('blob.delete_blob'):
            return HttpResponseForbidden()
        blob.reference_set.all().delete()
        blob.delete()
        return OKResponse({'deleted' : True})
    if request.method == 'GET' or request.method == 'HEAD':
        blob.save()
        if settings.USE_X_SENDFILE:
            return HttpResponse(headers={'X-Sendfile': blob.realpath}, content_type='application/octet-stream')
        return FileResponse(blob.open(), content_type='application/octet-stream')
    return HttpResponseNotAllowed(['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])
