# vim:ts=4:sts=4:sw=4:expandtab

import hashlib
import json
import os
import re
import requests
import sys

from kolejka.common import KolejkaTask, KolejkaResult

from .autoconfig import autoconfig

class KolejkaClient:
    def __init__(self, settings=None, **kwargs):
        if settings is None:
            settings = autoconfig()
        settings.update(kwargs)
        self.session = requests.session()
        self.settings = settings
        self.settings.update(self.get('/settings/').json())
    @property
    def instance(self):
        return self.settings['instance']
    def instance_url(self, url):
        if not re.search(r'^https?://', url):
            url = self.instance.rstrip('/') + '/' + url.lstrip('/')
        return url
    @property
    def instance_csrf(self):
        return self.session.cookies.get('csrftoken', '')
    @property
    def instance_session(self):
        return self.session.cookies.get('sessionid', '')

    def simple(self, method, *args, **kwargs):
        if len(args) >= 1:
            args = list(args)
            args[0] = self.instance_url(args[0])
        return method(*args, **kwargs)

    def complex(self, method, *args, **kwargs):
        if len(args) >= 1:
            args = list(args)
            args[0] = self.instance_url(args[0])
        headers = kwargs.get('headers', dict())
        headers['X-CSRFToken'] = self.instance_csrf
        kwargs['headers'] = headers
        result = method(*args, **kwargs)
        return result

    def head(self, *args, **kwargs):
        return self.simple(self.session.head, *args, **kwargs)
    def get(self, *args, **kwargs):
        return self.simple(self.session.get, *args, **kwargs)
    def post(self, *args, **kwargs):
        return self.complex(self.session.post, *args, **kwargs)
    def put(self, *args, **kwargs):
        return self.complex(self.session.put, *args, **kwargs)
    def delete(self, *args, **kwargs):
        return self.complex(self.session.delete, *args, **kwargs)

    def login(self, username=None, password=None):
        username = username or self.settings['username']
        password = password or self.settings['password']
        self.post('/accounts/login/', data={'username': username, 'password': password})

    def blob_put(self, blob_path):
        if not self.instance_session:
            self.login() 
        hasher = hashlib.new(self.settings['blob_hash_algorithm'])
        with open(blob_path, 'rb') as blob_file:
            while True:
                buf = blob_file.read(8192)
                if len(buf) == 0:
                    break
                hasher.update(buf)
            hash = hasher.hexdigest()
            info = self.post('/blob/blob/{}/'.format(hash), data={})
            if info.status_code == 200:
                reference = info.json()['reference']
                return reference
            else:
                blob_file.seek(0)
                info = self.post('/blob/reference/', data=blob_file)
                if info.status_code == 200:
                    reference = info.json()['reference']
                    return reference
                else:
                    print(info)
                    print(info.text)

    def blob_get(self, blob_path, blob_reference=None, blob_hash=None):
        if blob_reference is not None:
            response = self.get('/blob/reference/{}/'.format(blob_reference), stream=True)
        elif blob_hash is not None:
            response = self.get('/blob/blob/{}/'.format(blob_hash), stream=True)
        if response.status_code == 200:
            dir_path = os.path.dirname(os.path.abspath(blob_path))
            os.makedirs(dir_path, exist_ok=True)
            try:
                with open(blob_path, 'wb') as blob_file:
                    for chunk in response.iter_content():
                        if chunk:
                            blob_file.write(chunk)
            except:
                os.unlink(blob_path)
                raise
        else:
            print(response)
            print(response.text)

    def blob_check(self, blob_reference=None, blob_hash=None):
        if blob_reference is not None:
            response = self.head('/blob/reference/{}/'.format(blob_reference), stream=True)
        elif blob_hash is not None:
            response = self.head('/blob/blob/{}/'.format(blob_hash), stream=True)
        return response.status_code == 200

    def task_put(self, task):
        for k,f in task.files.items():
            if not f.reference or not self.blob_check(blob_reference = f.reference):
                f.reference = None
                if f.path:
                    f.reference = self.blob_put(os.path.join(task.path, f.path))['key']
                else:
                    raise 
        info = self.post('/task/task/', data=json.dumps(task.dump()))
        if info.status_code == 200:
            task = KolejkaTask(None)
            task.load(info.json()['task'])
            return task
        else:
            print(info)
            print(info.text)

    def task_get(self, task_key, task_path):
        response = self.get('/task/task/{}/'.format(task_key))
        if response.status_code == 200:
            os.makedirs(task_path, exist_ok=True)
            task = KolejkaTask(task_path)
            desc = response.json()['task']
            task.load(desc)
            for k,f in task.files.items():
                self.blob_get(os.path.join(task.path, k), f.reference)
                f.path = k
            task.commit()
            return task

    def result_put(self, result):
        for k,f in result.files.items():
            if not f.reference or not self.blob_check(blob_reference = f.reference):
                f.reference = None
                if f.path:
                    f.reference = self.blob_put(os.path.join(result.path, f.path))['key']
                else:
                    raise 
        info = self.post('/task/result/', data=json.dumps(result.dump()))
        if info.status_code == 200:
            result = KolejkaResult(None)
            result.load(info.json()['result'])
            return result
        else:
            print(info)
            print(info.text)

    def result_get(self, task_key, result_path):
        response = self.get('/task/result/{}/'.format(task_key))
        if response.status_code == 200:
            os.makedirs(result_path, exist_ok=True)
            result = KolejkaResult(result_path)
            desc = response.json()['result']
            result.load(desc)
            for k,f in result.files.items():
                self.blob_get(os.path.join(result.path, k), f.reference)
                f.path = k
            result.commit()
            return result
