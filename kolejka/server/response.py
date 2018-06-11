# vim:ts=4:sts=4:sw=4:expandtab

from django.http import JsonResponse

class OKResponse(JsonResponse):
    def __init__(self, data=None, **kwargs):
        if data is None:
            data = dict()
        for key, val in kwargs.items():
            data[key] = val
        assert isinstance(data, dict)
        assert 'status' not in data
        data['status'] = 'OK'
        super().__init__(data)

class FAILResponse(JsonResponse):
    def __init__(self, data=None, **kwargs):
        if data is None:
            data = dict()
        for key, val in kwargs.items():
            data[key] = val
        assert isinstance(data, dict)
        assert 'status' not in data
        data['status'] = 'FAIL'
        super().__init__(data)
