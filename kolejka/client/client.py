# vim:ts=4:sts=4:sw=4:expandtab

import hashlib
import json
import os
import re
import requests
import sys

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
        #self.get('/accounts/login/')
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
            info = self.put('/blob/hash/{}/'.format(hash), data={})
            if info.status_code == 200:
                reference = info.json()['reference']
            else:
                blob_file.seek(0)
                info = self.put('/blob/', data=blob_file)
                if info.status_code == 200:
                    reference = info.json()['reference']
        return reference

    def blob_get(self, blob_path, blob_key=None, blob_hash=None):
        if blob_key is not None:
            response = self.get('/blob/{}/'.format(blob_key), stream=True)
        elif blob_hash is not None:
            response = self.get('/blob/hash/{}/'.format(blob_hash), stream=True)
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
