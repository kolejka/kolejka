# vim:ts=4:sts=4:sw=4:expandtab

import copy
import glob
import json
import os

from .settings import TASK_SPEC, RESULT_SPEC
from .parse import parse_int, parse_str, parse_bool
from .parse import json_dict_load, json_list_load
from .limits import KolejkaLimits, KolejkaStats

class KolejkaCollect:
    class Collect:
        def __init__(self, **kwargs):
            self.load(kwargs)

        def load(self, data, **kwargs):
            args = json_dict_load(data)
            args.update(kwargs)
            self.glob = parse_str(args.get('glob'))
            self.strip = parse_int(args.get('strip', 0))
            self.prefix = parse_str(args.get('prefix', '')).strip('/')

        def dump(self):
            res = dict()
            res['glob'] = self.glob
            if self.strip > 0:
                res['strip'] = self.strip
            if self.prefix:
                res['prefix'] = self.prefix
            return res

        def collect(self, path=None):
            res = dict()
            if path:
                orig_path = os.getcwd()
                os.chdir(path)
            try:
                for f in glob.iglob(self.glob, recursive=True):
                    if os.path.isfile(f):
                        splited = f.split('/')
                        splited = splited[min(self.strip, len(splited)-1):]
                        striped = '/'.join(splited).strip('/')
                        if self.prefix:
                            striped = os.path.join(self.prefix, striped)
                        res[striped] = os.path.abspath(f)
            finally:
                if path:
                    os.chdir(orig_path)
            return res

    def __init__(self):
        self.load(list())

    def load(self, data):
        self.collect = list()
        for c in json_list_load(data):
            cc = KolejkaCollect.Collect()
            cc.load(c)
            self.collect.append(cc)

    def dump(self):
        res = list()
        for c in self.collect:
            res.append(c.dump())
        return res

    def collect(self, path=None):
        res = dict()
        for c in self.collect:
            res.update(c.collect(path))
        return res

class KolejkaFiles:
    class File:
        def __init__(self, spec):
            self.load(spec)

        def load(self, data):
            self.name = data.split(':')[0].split('@')[0]
            self.path = None
            self.reference = None
            simple = True
            if ':' in data:
                self.path = data.split(':')[1].split(':')[0].split('@')[0]
                simple = False
            if '@' in data:
                self.reference = data.split('@')[1].split(':')[0].split('@')[0]
                simple = False
            if simple:
                self.path = self.name

        def dump(self):
            res = self.name
            if self.path is not None:
                if self.path != self.name or self.reference is not None:
                    res += ':' + self.path
            if self.reference is not None:
                res += '@' + self.reference
            return res

        def is_local(self):
            return self.path is not None

        def is_contained(self, path):
            if self.path is not None:
                file_path = os.path.realpath(os.path.join(path, self.path))
                return file_path.startswith(os.path.realpath(path)+'/')
            return True

        def open(self, path=None, mode='rb'):
            if self.path is not None:
                return open(os.path.join(path or os.getcwd(), self.path), mode)

    def __init__(self, path=None, data=None):
        self.path = path
        self.files = dict()
        self.load(data)

    def load(self, data):
        args = json_dict_load(data)
        for arg in args:
            self.add(arg)

    def dump(self):
        res = list()
        for file_spec in self.files.values():
            res.append(file_spec.dump())
        return res

    @property
    def is_local(self):
        for file_spec in self.files.values():
            if not file_spec.is_local():
                return False
        return True

    @property
    def is_contained(self):
        if self.path is None:
            return False
        for file_spec in self.files.values():
            if not file_spec.is_contained(self.path):
                return False
        return True

    def items(self):
        return self.files.items()

    def add(self, spec):
        f = KolejkaFiles.File(spec)
        self.files[f.name] = f

    def remove(self, spec):
        f = KolejkaFiles.File(spec)
        if f.name in self.files:
            del self.files[f.name]

    def clear(self):
        self.files = dict()

class KolejkaTask():
    def __init__(self, path, **kwargs):
        self.path = path
        data = {}
        if self.path is not None:
            if os.path.exists(self.spec_path):
                with open(self.spec_path, 'r') as spec_file:
                    data = json.load(spec_file)
        self.load(data, **kwargs)

    @property
    def spec_path(self):
        if self.path is not None:
            return os.path.join(self.path, TASK_SPEC)

    def load(self, data, **kwargs):
        args = json_dict_load(data)
        args.update(kwargs)
        self.id = parse_str(args.get('id', None))
        self.image = parse_str(args.get('image', None))
        self.requires = args.get('requires', [])
        self.exclusive = parse_bool(args.get('exclusive', None))
        self.limits = KolejkaLimits()
        self.limits.load(args.get('limits', {}))
        self.environment = dict()
        for k, v in args.get('environment', {}).items():
            self.environment[str(k)] = str(v)
        self.args = [ str(k) for k in args.get('args', []) ]
        self.stdin = parse_str(args.get('stdin', None))
        self.stdout = parse_str(args.get('stdout', None))
        self.stderr = parse_str(args.get('stderr', None))
        self.files = KolejkaFiles(self.path)
        self.files.load(args.get('files', []))
        self.collect = KolejkaCollect()
        self.collect.load(args.get('collect', []))

    def dump(self):
        res = dict()
        if self.id is not None:
            res['id'] = self.id
        if self.image is not None:
            res['image'] = self.image
        res['requires'] = copy.copy(self.requires)
        if self.exclusive is not None:
            res['exclusive'] = self.exclusive
        res['limits'] = self.limits.dump()
        res['environment'] = copy.copy(self.environment)
        res['args'] = copy.copy(self.args)
        if self.stdin is not None:
            res['stdin'] = self.stdin
        if self.stdout is not None:
            res['stdout'] = self.stdout
        if self.stderr is not None:
            res['stderr'] = self.stderr
        res['files'] = self.files.dump()
        return res
    
    def commit(self):
        os.makedirs(os.path.dirname(self.spec_path), exist_ok=True)
        with open(self.spec_path, 'w') as spec_file:
            json.dump(self.dump(), spec_file, sort_keys=True, indent=2, ensure_ascii=False)

class KolejkaResult():
    def __init__(self, path, **kwargs):
        self.path = path
        data = {}
        if self.path is not None:
            if os.path.exists(self.spec_path):
                with open(self.spec_path, 'r') as spec_file:
                    data = json.load(spec_file)
        self.load(data, **kwargs)

    @property
    def spec_path(self):
        if self.path is not None:
            return os.path.join(self.path, RESULT_SPEC)

    def load(self, data, **kwargs):
        args = json_dict_load(data)
        args.update(kwargs)
        self.id = parse_str(args.get('id', None))
        self.tags = args.get('tags', [])
        self.limits = KolejkaLimits()
        self.limits.load(args.get('limits', {}))
        self.stats = KolejkaStats()
        self.stats.load(args.get('stats', {}))
        self.result = parse_int(args.get('result', None))
        self.stdout = parse_str(args.get('stdout', None))
        self.stderr = parse_str(args.get('stderr', None))
        self.files = KolejkaFiles(self.path)
        self.files.load(args.get('files', []))

    def dump(self):
        res = dict()
        if self.id is not None:
            res['id'] = self.id
        res['tags'] = copy.copy(self.tags)
        res['limits'] = self.limits.dump()
        res['stats'] = self.stats.dump()
        if self.result is not None:
            res['result'] = self.result
        if self.stdout is not None:
            res['stdout'] = self.stdout
        if self.stderr is not None:
            res['stderr'] = self.stderr
        res['files'] = self.files.dump()
        return res
    
    def commit(self):
        os.makedirs(os.path.dirname(self.spec_path), exist_ok=True)
        with open(self.spec_path, 'w') as spec_file:
            json.dump(self.dump(), spec_file, sort_keys=True, indent=2, ensure_ascii=False)
