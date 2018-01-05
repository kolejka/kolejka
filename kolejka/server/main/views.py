# vim:ts=4:sts=4:sw=4:expandtab

import django.conf
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound, StreamingHttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie

from kolejka.common import KolejkaLimits

def index(request):
    return HttpResponse("INDEX")

@ensure_csrf_cookie
def settings(request):
    settings = django.conf.settings
    if request.method == 'GET':
        response = dict()
        response['blob_hash_algorithm'] = settings.BLOB_HASH_ALGORITHM
        limits = KolejkaLimits(
                cpus=settings.LIMIT_CPUS,
                memory=settings.LIMIT_MEMORY,
                pids=settings.LIMIT_PIDS,
                storage=settings.LIMIT_STORAGE,
                network=settings.LIMIT_NETWORK,
                time=settings.LIMIT_TIME,
            )
        response['limits'] = limits.dump()
        return JsonResponse(response)
