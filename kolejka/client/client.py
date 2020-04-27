# vim:ts=4:sts=4:sw=4:expandtab

import hashlib
import json
import logging
import os
import re
import requests
import shutil
import sys
import time

from kolejka.common import kolejka_config, client_config
from kolejka.common import KolejkaTask, KolejkaResult, KolejkaLimits
from kolejka.common import MemoryAction, TimeAction

class KolejkaClientError(Exception):
    pass

class KolejkaClientAuthorizationError(KolejkaClientError):
    pass

class KolejkaClientObjectNotFoundError(KolejkaClientError):
    pass

class KolejkaClientRemoteError(KolejkaClientError):
    pass

class KolejkaClientDownloadError(KolejkaClientError):
    pass

class KolejkaClientUploadError(KolejkaClientError):
    pass

class KolejkaClient:
    def __init__(self, max_retries=3):
        self.config = client_config()
        self.session = requests.session()
        if max_retries is not None:
            adapter = requests.adapters.HTTPAdapter(max_retries=max_retries)
            self.session.mount('http://', adapter)
            self.session.mount('https://', adapter)
        if self.config.username is not None and self.config.password is not None:
            self.login()
        for k,v in self.get('/settings/').json().items():
            self.config.__setattr__(k, v)
    @property
    def instance(self):
        url = self.config.server
        if not re.search(r'^https?://', url):
            url = 'https://'+url
        return url
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

    def check_response(self, response):
        if response.status_code == requests.codes.forbidden:
            response.close()
            raise KolejkaClientAuthorizationError()
        if response.status_code == requests.codes.not_found:
            response.close()
            raise KolejkaClientObjectNotFoundError()
        if response.status_code != requests.codes.ok:
            response.close()
            raise KolejkaClientRemoteError()
        if response.headers.get('content-type','') == 'application/json':
            j = response.json()
            if isinstance(j, dict) and 'status' in j:
                if j['status'] != 'OK':
                    if 'message' in j:
                        response.close()
                        raise KolejkaClientRemoteError(j['message'])
                    response.close()
                    raise KolejkaClientRemoteError()
        return response

    def simple(self, method, *args, **kwargs):
        if len(args) >= 1:
            args = list(args)
            args[0] = self.instance_url(args[0])
        headers = kwargs.get('headers', dict())
        headers['Referer'] = self.instance
        kwargs['headers'] = headers
        return self.check_response( method(*args, **kwargs))

    def complex(self, method, *args, **kwargs):
        if len(args) >= 1:
            args = list(args)
            args[0] = self.instance_url(args[0])
        headers = kwargs.get('headers', dict())
        headers['X-CSRFToken'] = self.instance_csrf
        headers['Referer'] = self.instance
        kwargs['headers'] = headers
        return self.check_response( method(*args, **kwargs))

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
        username = username or self.config.username
        password = password or self.config.password
        assert username and password
        self.get('/logout/') #CLEARS USER AND ENSURES CSRF
        response = self.post('/login/', data={'username': username, 'password': password})

    def logout(self):
        response = self.post('/logout/')

    def blob_put(self, blob_path):
        assert os.path.isfile(blob_path)
        if not self.instance_session:
            self.login() 
        hasher = hashlib.new(self.config.blob_hash_algorithm)
        with open(blob_path, 'rb') as blob_file:
            while True:
                buf = blob_file.read(8192)
                if len(buf) == 0:
                    break
                hasher.update(buf)
            hash = hasher.hexdigest()
            try:
                response = self.post('/blob/blob/{}/'.format(hash), data={})
                reference = response.json()['reference']
                return reference
            except KolejkaClientObjectNotFoundError:
                blob_file.seek(0)
                response = self.post('/blob/reference/', data=blob_file)
                reference = response.json()['reference']
                return reference
        raise KolejkaClientError()

    def blob_get(self, blob_path, blob_reference=None, blob_hash=None):
        assert blob_reference or blob_hash
        if blob_reference is not None:
            response = self.get('/blob/reference/{}/'.format(blob_reference), stream=True)
        elif blob_hash is not None:
            response = self.get('/blob/blob/{}/'.format(blob_hash), stream=True)
        dir_path = os.path.dirname(os.path.abspath(blob_path))
        os.makedirs(dir_path, exist_ok=True)
        try:
            with open(blob_path, 'wb') as blob_file:
                for chunk in response.iter_content():
                    if chunk:
                        blob_file.write(chunk)
        except:
            os.unlink(blob_path)
            raise KolejkaClientDownloadError()

    def blob_del(self, blob_reference=None, blob_hash=None):
        assert blob_reference or blob_hash
        try:
            if blob_reference is not None:
                response = self.delete('/blob/reference/{}/'.format(blob_reference))
            elif blob_hash is not None:
                response = self.delete('/blob/blob/{}/'.format(blob_hash))
        except KolejkaClientObjectNotFoundError:
            pass

    def blob_check(self, blob_reference=None, blob_hash=None):
        try:
            if blob_reference is not None:
                response = self.head('/blob/reference/{}/'.format(blob_reference), stream=True)
            elif blob_hash is not None:
                response = self.head('/blob/blob/{}/'.format(blob_hash), stream=True)
            return True
        except KolejkaClientObjectNotFoundError:
            return False

    def task_put(self, task):
        limits = KolejkaLimits()
        limits.cpus = self.config.cpus
        limits.memory = self.config.memory
        limits.swap = self.config.swap
        limits.pids = self.config.pids
        limits.storage = self.config.storage
        limits.image = self.config.image
        limits.workspace = self.config.workspace
        limits.time = self.config.time
        limits.network = self.config.network
        task.limits.update(limits)
        if not self.instance_session:
            self.login() 
        for f in task.files.values():
            if not f.reference or not self.blob_check(blob_reference = f.reference):
                assert f.path
                f.reference = self.blob_put(os.path.join(task.path, f.path))['key']
        response = self.post('/task/task/', data=json.dumps(task.dump()))
        task = KolejkaTask(None)
        task.load(response.json()['task'])
        return task

    def task_get(self, task_key, task_path):
        if isinstance(task_key, KolejkaTask):
            task_key = task_key.id
        response = self.get('/task/task/{}/'.format(task_key))
        os.makedirs(task_path, exist_ok=True)
        task = KolejkaTask(task_path)
        task.load(response.json()['task'])
        for k,f in task.files.items():
            self.blob_get(os.path.join(task.path, k), f.reference)
            f.path = k
        task.commit()
        return task

    def task_del(self, task_key):
        if isinstance(task_key, KolejkaTask):
            task_key = task_key.id
        try:
            response = self.delete('/task/task/{}/'.format(task_key))
        except KolejkaClientObjectNotFoundError:
            pass

    def result_put(self, result):
        if not self.instance_session:
            self.login() 
        for f in result.files.values():
            if not f.reference or not self.blob_check(blob_reference = f.reference):
                assert f.path
                f.reference = self.blob_put(os.path.join(result.path, f.path))['key']
        response = self.post('/task/result/', data=json.dumps(result.dump()))
        result = KolejkaResult(None)
        result.load(response.json()['result'])
        return result

    def result_get(self, task_key, result_path):
        response = self.get('/task/result/{}/'.format(task_key))
        os.makedirs(result_path, exist_ok=True)
        result = KolejkaResult(result_path)
        desc = response.json()['result']
        result.load(desc)
        for k,f in result.files.items():
            self.blob_get(os.path.join(result.path, k), f.reference)
            f.path = k
        result.commit()
        return result

    def result_del(self, result_key):
        if isinstance(result_key, KolejkaTask):
            result_key = result_key.id
        if isinstance(result_key, KolejkaResult):
            result_key = result_key.id
        try:
            response = self.delete('/task/result/{}/'.format(result_key))
        except KolejkaClientObjectNotFoundError:
            pass

    def dequeue(self, concurency, limits, tags):
        if not self.instance_session:
            self.login() 
        response = self.post('/queue/dequeue/', data=json.dumps({'concurency' : concurency, 'limits' : limits.dump(), 'tags' : tags}))
        ts = response.json()['tasks']
        tasks = list()
        for t in ts:
            tt = KolejkaTask(None)
            tt.load(t)
            tasks.append(tt)
        return tasks

def config_parser_blob_put(parser):
    parser.add_argument('file', type=str, help='file')
    def execute(args):
        kolejka_config(args=args)
        client = KolejkaClient()
        response = client.blob_put(args.file)
        print(response['key'])
    parser.set_defaults(execute=execute)

def config_parser_blob_get(parser):
    parser.add_argument('reference', type=str, help='reference key')
    parser.add_argument('path', type=str, help='result path')
    def execute(args):
        kolejka_config(args=args)
        client = KolejkaClient()
        client.blob_get(args.path, blob_reference=args.reference)
    parser.set_defaults(execute=execute)

def config_parser_blob_del(parser):
    parser.add_argument('reference', type=str, help='reference key')
    def execute(args):
        kolejka_config(args=args)
        client = KolejkaClient()
        client.blob_del(blob_reference=args.reference)
    parser.set_defaults(execute=execute)

def config_parser_blob(parser):
    subparsers = parser.add_subparsers(dest='subcommand')
    subparsers.required = True
    subparser = subparsers.add_parser('put')
    config_parser_blob_put(subparser)
    subparser = subparsers.add_parser('get')
    config_parser_blob_get(subparser)
    subparser = subparsers.add_parser('delete')
    config_parser_blob_del(subparser)

def config_parser_task_put(parser):
    parser.add_argument('task', type=str, help='task folder')
    parser.add_argument('--cpus', type=int, help='cpus limit')
    parser.add_argument('--memory', action=MemoryAction, help='memory limit')
    parser.add_argument('--swap', action=MemoryAction, help='swap limit')
    parser.add_argument('--pids', type=int, help='pids limit')
    parser.add_argument('--storage', action=MemoryAction, help='storage limit')
    parser.add_argument('--image', action=MemoryAction, help='image size limit')
    parser.add_argument('--workspace', action=MemoryAction, help='workspace size limit')
    parser.add_argument('--time', action=TimeAction, help='time limit')
    parser.add_argument('--network',type=bool, help='allow netowrking')
    def execute(args):
        kolejka_config(args=args)
        client = KolejkaClient()
        task = KolejkaTask(args.task)
        response = client.task_put(task)
        print(response.id)
    parser.set_defaults(execute=execute)

def config_parser_task_get(parser):
    parser.add_argument('task', type=str, help='task key')
    parser.add_argument('path', type=str, help='task folder')
    def execute(args):
        kolejka_config(args=args)
        client = KolejkaClient()
        client.task_get(args.task, args.path)
    parser.set_defaults(execute=execute)

def config_parser_task_del(parser):
    parser.add_argument('task', type=str, help='task key')
    def execute(args):
        kolejka_config(args=args)
        client = KolejkaClient()
        client.task_del(args.task)
    parser.set_defaults(execute=execute)

def config_parser_task(parser):
    subparsers = parser.add_subparsers(dest='subcommand')
    subparsers.required = True
    subparser = subparsers.add_parser('put')
    config_parser_task_put(subparser)
    subparser = subparsers.add_parser('get')
    config_parser_task_get(subparser)
    subparser = subparsers.add_parser('delete')
    config_parser_task_del(subparser)

def config_parser_result_put(parser):
    parser.add_argument('result', type=str, help='result folder')
    def execute(args):
        kolejka_config(args=args)
        client = KolejkaClient()
        result = KolejkaResult(args.result)
        client.result_put(result)
    parser.set_defaults(execute=execute)

def config_parser_result_get(parser):
    parser.add_argument('task', type=str, help='task key')
    parser.add_argument('path', type=str, help='result folder')
    def execute(args):
        kolejka_config(args=args)
        client = KolejkaClient()
        client.result_get(args.task, args.path)
    parser.set_defaults(execute=execute)

def config_parser_result_del(parser):
    parser.add_argument('task', type=str, help='task key')
    def execute(args):
        kolejka_config(args=args)
        client = KolejkaClient()
        client.result_del(args.task)
    parser.set_defaults(execute=execute)

def config_parser_result(parser):
    subparsers = parser.add_subparsers(dest='subcommand')
    subparsers.required = True
    subparser = subparsers.add_parser('put')
    config_parser_result_put(subparser)
    subparser = subparsers.add_parser('get')
    config_parser_result_get(subparser)
    subparser = subparsers.add_parser('delete')
    config_parser_result_del(subparser)

def config_parser_execute(parser):
    parser.add_argument('task', type=str, help='task folder')
    parser.add_argument('result', type=str, help='result folder')
    parser.add_argument('--interval', type=float, default=5, help='result query interval (in seconds)')
    parser.add_argument('--consume', action='store_true', default=False, help='consume task folder') 
    parser.add_argument('--cpus', type=int, help='cpus limit')
    parser.add_argument('--memory', action=MemoryAction, help='memory limit')
    parser.add_argument('--swap', action=MemoryAction, help='swap limit')
    parser.add_argument('--pids', type=int, help='pids limit')
    parser.add_argument('--storage', action=MemoryAction, help='storage limit')
    parser.add_argument('--image', action=MemoryAction, help='image size limit')
    parser.add_argument('--workspace', action=MemoryAction, help='workspace size limit')
    parser.add_argument('--time', action=TimeAction, help='time limit')
    parser.add_argument('--network',type=bool, help='allow netowrking')
    def execute(args):
        kolejka_config(args=args)
        client = KolejkaClient()
        task = KolejkaTask(args.task)
        response = client.task_put(task)
        while True:
            client.session.close()
            time.sleep(args.interval)
            try:
                result = client.result_get(response.id, args.result)
            except KolejkaClientObjectNotFoundError:
                continue
            if args.consume:
                shutil.rmtree(args.task)
            break
    parser.set_defaults(execute=execute)

def config_parser(parser):
    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True
    subparser = subparsers.add_parser('blob')
    config_parser_blob(subparser)
    subparser = subparsers.add_parser('task')
    config_parser_task(subparser)
    subparser = subparsers.add_parser('result')
    config_parser_result(subparser)
    subparser = subparsers.add_parser('execute')
    config_parser_execute(subparser)
