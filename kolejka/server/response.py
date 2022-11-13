# vim:ts=4:sts=4:sw=4:expandtab

from django.conf import settings

from django.http import JsonResponse

class OKResponse(JsonResponse):
    def __init__(self, __data=None, **kwargs):
        if __data is None:
            __data = dict()
        assert isinstance(__data, dict)
        for key, val in kwargs.items():
            __data[key] = val
        assert 'status' not in __data
        __data['status'] = 'OK'
        super().__init__(__data)

class FAILResponse(JsonResponse):
    def __init__(self, __data=None, **kwargs):
        if __data is None:
            __data = dict()
        assert isinstance(__data, dict)
        for key, val in kwargs.items():
            __data[key] = val
        assert 'status' not in __data
        __data['status'] = 'FAIL'
        super().__init__(__data)
