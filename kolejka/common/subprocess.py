# vim:ts=4:sts=4:sw=4:expandtab

from kolejka.common import settings

import base64
import datetime
import json
import os
import re
import signal
import subprocess
import time

class Process:
    def __init__(self, starter, process, start_time):
        self.starter = starter
        self.process = process
        self.start_time = start_time
    @property
    def args(self):
        return self.starter.args
    @property
    def stdin(self):
        return self.process.stdin
    @property
    def stdout(self):
        return self.process.stdout
    @property
    def stderr(self):
        return self.process.stderr
    @property
    def pid(self):
        return self.process.pid
    def __enter__(self):
        return self
    def __exit__(self, exc_type, value, traceback):
        self.process.__exit__(exc_type, value, traceback)
    def communicate(self, *args, **kwargs):
        return self.process.communicate(*args, **kwargs)
    def poll(self, *args, **kwargs):
        return self.process.poll(*args, **kwargs)
    def wait(self, *args, **kwargs):
        return self.process.wait(*args, **kwargs)
    def send_signal(self, *args, **kwargs):
        return self.process.send_signal(*args, **kwargs)
    def terminate(self, *args, **kwargs):
        return self.process.terminate(*args, **kwargs)
    def kill(self, *args, **kwargs):
        return self.process.kill(*args, **kwargs)

class CompletedProcess:
    def __init__(self, starter, returncode, stdout=None, stderr=None, time=None, start_time=None, stop_time=None):
        self.starter = starter
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.time = time
        if self.time is None and start_time is not None and stop_time is not None and stop_time >= start_time:
            self.time = datetime.timedelta(seconds=stop_time - start_time)
    @property
    def args(self):
        return self.starter.args

class Starter:
    def __init__(self, args, executable=None, preexec_fn=None, stdin=None, stdout=None, stderr=None, chroot=None, cwd=None, umask=None, nice=None, script_env=None, env=None, user=None, group=None, groups=None, resources=None, **kwargs):
        if executable is not None:
            raise ValueError('executable is not supported')
        if preexec_fn is not None:
            raise ValueError('preexec_fn is not supported')

        if isinstance(args, (str, bytes, os.PathLike)):
            args = [args]
        else:
            args = list(args)
        self.args = args

        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

        self.chroot = chroot
        self.cwd = cwd
        self.umask = umask
        self.nice = nice
        self.script_env = script_env or dict(os.environ)
        self.env = env or dict(os.environ)
        self.user = user
        self.group = group
        self.groups = groups
        self.resources = resources

        self.kwargs = kwargs

    @property
    def imports(self):
        return self.get_imports()
    def get_imports(self):
        return set([ 'base64', 'json', 'os', 'resource', 'sys' ])

    @staticmethod
    def represent(obj):
        if isinstance(obj, (bytes,)):
            return 'base64.urlsafe_b64decode(\''+str(base64.urlsafe_b64encode(obj), 'utf-8')+'\')'
        if isinstance(obj, os.PathLike):
            obj = str(obj)
        safe = str(base64.urlsafe_b64encode(bytes(json.dumps(obj), 'utf-8')), 'utf-8')
        return 'json.loads(base64.urlsafe_b64decode(\''+safe+'\'))'

    @property
    def commands(self):
        return self.get_commands()
    def get_commands(self):
        commands = list()
        if self.nice is not None:
            commands.append(f'os.nice({self.represent(self.nice)})')
        if self.umask is not None:
            commands.append(f'os.umask({self.represent(self.umask)})')
        if self.chroot is not None:
            commands.append(f'os.chroot({self.represent(self.chroot)})')
        if self.cwd is not None:
            commands.append(f'os.chdir({self.represent(self.cwd)})')
        if self.group is not None:
            commands.append(f'os.setgid({self.represent(self.group)})')
        if self.groups is not None:
            commands.append(f'os.setgroups({self.represent(self.groups)})')
        if self.resources:
            for key,val in self.resources.items():
                commands.append(f'resource.setrlimit({self.represent(key)},({self.represent(val[0])},{self.represent(val[1])}))')
        if self.user is not None:
            commands.append(f'os.setuid({self.represent(self.user)})')

        return commands

    @property
    def script(self):
        return self.get_script()
    def get_script(self):
        lines = list()
        for imp in self.imports:
            lines.append(f'import {imp}')
        for command in self.commands:
            lines.append(command)
        executable = self.args[0]
        lines.append(f'os.execvpe({self.represent(executable)},{self.represent(self.args)},{self.represent(self.env)})')
        lines = [ re.sub(r'["]', '\\\"', line) for line in lines ]
        all_lines = '\n'.join(lines)
        return all_lines

    def __call__(self):
        self.script_env['__KOLEJKA_STARTER_SCRIPT__'] = self.script
        return Process(
            starter=self,
            process=subprocess.Popen(args=['python3', '-c', 'import os; exec(os.environ.get(\'__KOLEJKA_STARTER_SCRIPT__\'));'], executable='python3', stdin=self.stdin, stdout=self.stdout, stderr=self.stderr, env=self.script_env, **self.kwargs),
            start_time=time.perf_counter(),
        )

def start(*args, _Starter=Starter, **kwargs):
    return _Starter(*args, **kwargs)()

def wait(process, input=None, timeout=None, check=False):
    stop_time = None
    try:
        stdout, stderr = process.communicate(input, timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        raise subprocess.TimeoutExpired(starter.args, timeout, output=stdout, stderr=stderr)
    except:
        process.kill()
        process.wait()
        raise
    retcode = process.poll()
    stop_time = time.perf_counter()
    if check and retcode:
        raise subprocess.CalledProcessError(retcode, starter.args, output=stdout, stderr=stderr)
    return CompletedProcess(process.starter, retcode, stdout, stderr, start_time=process.start_time, stop_time=stop_time)

def run(*args, _Starter=Starter, input=None, timeout=None, check=False, **kwargs):
    if input is not None:
        if 'stdin' in kwargs:
            raise ValueError('stdin and input arguments can not be used simultaneously.')
        kwargs['stdin'] = subprocess.PIPE

    with start(*args, _Starter=_Starter, **kwargs) as process:
        return wait(process, input=input, timeout=timeout, check=check)
