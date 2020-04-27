# vim:ts=4:sts=4:sw=4:expandtab

import django.conf
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound, StreamingHttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie

from kolejka.common import KolejkaLimits
from kolejka.server.response import OKResponse, FAILResponse

@ensure_csrf_cookie
def index(request):
    return HttpResponse("INDEX")

def settings(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    settings = django.conf.settings
    response = dict()
    response['blob_hash_algorithm'] = settings.BLOB_HASH_ALGORITHM
    limits = KolejkaLimits(
            cpus=settings.LIMIT_CPUS,
            memory=settings.LIMIT_MEMORY,
            swap=settings.LIMIT_SWAP,
            pids=settings.LIMIT_PIDS,
            storage=settings.LIMIT_STORAGE,
            image=settings.LIMIT_IMAGE,
            workspace=settings.LIMIT_WORKSPACE,
            network=settings.LIMIT_NETWORK,
            time=settings.LIMIT_TIME,
        )
    response['limits'] = limits.dump()
    return OKResponse(response)

@ensure_csrf_cookie
def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return OKResponse({})
        return FAILResponse({})
    if request.method == 'GET':
        return OKResponse({})
    return HttpResponseNotAllowed(['GET', 'POST'])

@ensure_csrf_cookie
def logout(request):
    auth_logout(request)
    return OKResponse({})
