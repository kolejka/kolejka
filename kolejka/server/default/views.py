# vim:ts=4:sts=4:sw=4:expandtab

from django.conf import settings as django_settings

from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotFound, StreamingHttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie

from kolejka.common.limits import KolejkaLimits
from kolejka.server.response import OKResponse, FAILResponse

@ensure_csrf_cookie
def index(request):
    return HttpResponse("INDEX")

def settings(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    response = dict()
    response['blob_hash_algorithm'] = django_settings.BLOB_HASH_ALGORITHM
    limits = KolejkaLimits(
            cpus=django_settings.LIMIT_CPUS,
            memory=django_settings.LIMIT_MEMORY,
            swap=django_settings.LIMIT_SWAP,
            pids=django_settings.LIMIT_PIDS,
            storage=django_settings.LIMIT_STORAGE,
            image=django_settings.LIMIT_IMAGE,
            workspace=django_settings.LIMIT_WORKSPACE,
            network=django_settings.LIMIT_NETWORK,
            time=django_settings.LIMIT_TIME,
            gpus=django_settings.LIMIT_GPUS,
            gpu_memory=django_settings.LIMIT_GPU_MEMORY,
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
            return OKResponse()
        return FAILResponse()
    if request.method == 'GET':
        return OKResponse()
    return HttpResponseNotAllowed(['GET', 'POST'])

@ensure_csrf_cookie
def logout(request):
    auth_logout(request)
    return OKResponse()
