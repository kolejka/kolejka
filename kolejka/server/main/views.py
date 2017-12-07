# vim:ts=4:sts=4:sw=4:expandtab

import django.conf
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound, StreamingHttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie

def index(request):
    return HttpResponse("INDEX")

@ensure_csrf_cookie
def settings(request):
    if request.method == 'GET':
        response = dict()
        response['blob_hash_algorithm'] = django.conf.settings.BLOB_HASH_ALGORITHM
        return JsonResponse(response)
