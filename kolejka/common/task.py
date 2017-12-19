# vim:ts=4:sts=4:sw=4:expandtab

import json
import os

from .settings import TASK_SPEC, RESULT_SPEC
from .parse import parse_time, parse_memory
from .parse import unparse_time, unparse_memory

class KolejkaFile:
    def __init__(self, path=None, reference=None):
        assert path is not None or reference is not None
        self.path = path
        self.reference = reference

    @property
    def is_local(self):
        return self.path is not None

    def is_contained(self, path):
        if self.path is not None:
            file_path = os.path.realpath(os.path.join(path, self.path))
            return file_path.startswith(os.path.realpath(path)+'/')
        return True

    def open(self, mode):
        if self.path:
            return open(self.path, mode)

class FileContainer:
    def __init__(self, path, spec_path):
        assert os.path.isdir(path)
        self.path = path
        self.spec = dict()
        self.spec_path = os.path.join(path, spec_path)
        if os.path.exists(self.spec_path):
            assert os.path.isfile(self.spec_path)
            with open(self.spec_path) as spec_file:
                self.spec = json.load(spec_file)
        self.files = dict()
        for file_spec in self.spec.get('files', list()):
            self.add_file(file_spec)

    @property
    def is_local(self):
        for f in self.files:
            if not f.is_local:
                return False
        return True

    @property
    def is_contained(self):
        for f in self.files:
            if not f.is_contained(self.path):
                return False
        return True

    def add_file(self, file_spec):
        file_path = file_spec.split(':@')[0]
        real_path = file_path
        file_reference = None
        if '@' in file_spec:
            file_reference = file_spec.split('@')[1].split(':@')[0]
        if ':' in file_spec:
            real_path = file_spec.slit(':')[1].slit(':@')[0]
        self.files[file_path] = KolejkaFile(path=real_path, reference=file_reference)

    def del_file(self, file_spec):
        file_path = file_spec.split(':@')[0]
        if file_path in self.files:
            del self.files[file_path]

    def commit_files(self):
        self.spec['files'] = list()
        for k, f in self.files.items():
            if f.is_local:
                if f.is_contained(self.path):
                    self.spec['files'].append(k)
                else:
                    self.spec['files'].append(k+':'+f.path)
            else:
                self.spec['files'].append(k+'@'+f.reference)

    def commit(self):
        self.commit_files()
        with open(self.spec_path, 'w') as spec_file:
            json.dump(self.spec, spec_file, sort_keys=True, indent=2, ensure_ascii=False)

class KolejkaTask(FileContainer):
    def __init__(self, path):
        super().__init__(path, TASK_SPEC)

    @property
    def id(self):
        if 'id' in self.spec:
            return str(self.spec['id'])
    @id.setter
    def id(self, val):
        if val is None:
            if 'id' in self.spec:
                del self.spec['id']
        else:
            self.spec['id'] = str(val)

    @property
    def image(self):
        if 'image' in self.spec:
            return str(self.spec['image'])
    @image.setter
    def image(self, val):
        if val is None:
            if 'image' in self.spec:
                del self.spec['image']
        else:
            self.spec['image'] = str(val)

    @property
    def memory(self):
        if 'memory' in self.spec:
            return parse_memory(self.spec['memory'])
    @memory.setter
    def memory(self, val):
        if val is None:
            if 'memory' in self.spec:
                del self.spec['memory']
        else:
            self.spec['memory'] = unparse_memory(val)

    @property
    def cpus(self):
        if 'cpus' in self.spec:
            return int(self.spec['cpus'])
    @cpus.setter
    def cpus(self, val):
        if val is None:
            if 'cpus' in self.spec:
                del self.spec['cpus']
        else:
            self.spec['cpus'] = int(val)

    @property
    def time(self):
        if 'time' in self.spec:
            return parse_time(self.spec['time'])
    @time.setter
    def time(self, val):
        if val is None:
            if 'time' in self.spec:
                del self.spec['time']
        else:
            self.spec['time'] = unparse_time(val)

    @property
    def pids(self):
        if 'pids' in self.spec:
            return int(self.spec['pids'])
    @pids.setter
    def pids(self, val):
        if val is None:
            if 'pids' in self.spec:
                del self.spec['pids']
        else:
            self.spec['pids'] = int(val)

    @property
    def environment(self):
        env = dict()
        if 'environment' in self.spec:
            for k, v in self.spec['environment'].items():
                env[str(k)] = str(v)
        return env
    @environment.setter
    def environment(self, val):
        if val is None:
            if 'environment' in self.spec:
                del self.spec['environment']
        else:
            self.spec['environment'] = dict([ (str(k), str(v)) for (k, v) in val.items() ])

    @property
    def args(self):
        if 'args' in self.spec:
            return [ str(s) for s in self.spec['args'] ]
    @args.setter
    def args(self, val):
        if val is None:
            if 'args' in self.spec:
                del self.spec['args']
        else:
            self.spec['args'] = [ str(s) for s in val ]

    @property
    def stdin(self):
        if 'stdin' in self.spec:
            return str(self.spec['stdin'])
    @stdin.setter
    def stdin(self, val):
        if val is None:
            if 'stdin' in self.spec:
                del self.spec['stdin']
        else:
            self.spec['stdin'] = str(val)

    @property
    def stdout(self):
        if 'stdout' in self.spec:
            return str(self.spec['stdout'])
    @stdout.setter
    def stdout(self, val):
        if val is None:
            if 'stdout' in self.spec:
                del self.spec['stdout']
        else:
            self.spec['stdout'] = str(val)

    @property
    def stderr(self):
        if 'stderr' in self.spec:
            return str(self.spec['stderr'])
    @stderr.setter
    def stderr(self,val):
        if val is None:
            if 'stderr' in self.spec:
                del self.spec['stderr']
        else:
            self.spec['stderr'] = str(val)

class KolejkaResult(FileContainer):
    def __init__(self, path):
        super().__init__(path, RESULT_SPEC)

    @property
    def id(self):
        if 'id' in self.spec:
            return str(self.spec['id'])
    @id.setter
    def id(self, val):
        if val is None:
            if 'id' in self.spec:
                del self.spec['id']
        else:
            self.spec['id'] = str(val)

    @property
    def time(self):
        if 'time' in self.spec:
            return parse_time(self.spec['time'])
    @time.setter
    def time(self, val):
        if val is None:
            if 'time' in self.spec:
                del self.spec['time']
        else:
            self.spec['time'] = unparse_time(val)

    @property
    def result(self):
        if 'result' in self.spec:
            return int(self.spec['result'])
    @result.setter
    def result(self, val):
        if val is None:
            if 'result' in self.spec:
                del self.spec['result']
        else:
            self.spec['result'] = int(val)

    @property
    def stats(self):
        if 'stats' in self.spec:
            return self.spec['stats']
    @stats.setter
    def stats(self, val):
        if val is None:
            if 'stats' in self.spec:
                del self.spec['stats']
        else:
            self.spec['stats'] = val

    @property
    def stdout(self):
        if 'stdout' in self.spec:
            return str(self.spec['stdout'])
    @stdout.setter
    def stdout(self, val):
        if val is None:
            if 'stdout' in self.spec:
                del self.spec['stdout']
        else:
            self.spec['stdout'] = str(val)

    @property
    def stderr(self):
        if 'stderr' in self.spec:
            return str(self.spec['stderr'])
    @stderr.setter
    def stderr(self,val):
        if val is None:
            if 'stderr' in self.spec:
                del self.spec['stderr']
        else:
            self.spec['stderr'] = str(val)
