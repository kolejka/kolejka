# vim:ts=4:sts=4:sw=4:expandtab

__import__('pkg_resources').declare_namespace('kolejka')

import argparse
import datetime
import json
import logging
import math
import os
import shutil
import subprocess
import sys
import tempfile

from kolejka.common import settings
from kolejka.common import parse_memory, parse_time
from kolejka.observer.client import KolejkaObserverClient

parser = argparse.ArgumentParser(description='KOLEJKA worker')
parser.add_argument('--stage', type=int, default=0)
parser.add_argument('task', nargs='?', default='TASK')
parser.add_argument('result', nargs='?', default='RESULT')
parser.add_argument('--temp-dir', type=str, default=None)
args = parser.parse_args()

worker_path = os.path.realpath(os.path.abspath(__file__))
worker_dir_path = os.path.dirname(worker_path)

task_path = os.path.realpath(os.path.abspath(args.task))
assert os.path.isdir(task_path)

task_spec_path = os.path.join(task_path, 'kolejka_task.json')
assert os.path.isfile(task_spec_path)

result_path = os.path.join(task_path, 'result')
result_spec_path = os.path.join(result_path, 'kolejka_result.json')

with open(task_spec_path, 'r') as task_file:
    task_spec = json.load(task_file)

task_files = dict()
for file in task_spec['files']:
    file_path = os.path.realpath(os.path.join(task_path, file))
    assert file_path.startswith(task_path+'/')
    assert os.path.isfile(file_path)
    file_subpath = file_path[len(task_path)+1:]
    task_files[file_subpath] = file_path

def silent_call(*args, **kwargs):
    kwargs['stdin'] = kwargs.get('stdin', subprocess.DEVNULL)
    kwargs['stdout'] = kwargs.get('stderr', subprocess.DEVNULL)
    kwargs['stderr'] = kwargs.get('stdout', subprocess.DEVNULL)
    return subprocess.call(*args, **kwargs)

def stage0():
    task_files['kolejka_task.json'] = task_spec_path
    docker_task = 'kolejka_task_{}'.format(task_spec['id'])

    docker_cleanup  = [
        [ 'docker', 'kill', docker_task ],
        [ 'docker', 'rm', docker_task ],
    ]

    with tempfile.TemporaryDirectory(dir=args.temp_dir) as jailed_path:
        os.makedirs(os.path.join(jailed_path, 'TASK'), exist_ok=True)
        for key, val in task_files.items():
            file_path = os.path.join(jailed_path, key)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as create_file:
                pass
        docker_call  = [ 'docker', 'run' ]
#        docker_call += [ '--cgroup-parent', docker_task ]
        docker_call += [ '--cpus', str(int(task_spec['cpus'])) ]
        for device in task_spec['devices'] :
            docker_call += [ '--device', device ]
        docker_call += [ '--entrypoint', '/opt/kolejka/kolejka-worker' ]
        for key, val in task_spec['environment'].items():
            docker_call += [ '--env', '{}={}'.format(key, val) ]
        docker_call += [ '--hostname', 'kolejka' ]
        docker_call += [ '--init' ]
        docker_call += [ '--memory', str(parse_memory(task_spec['memory'])) ]
        docker_call += [ '--memory-swap', str(0) ]
        docker_call += [ '--cap-add', 'SYS_NICE' ]
        docker_call += [ '--name', docker_task ]
        docker_call += [ '--pids-limit', str(int(task_spec['pids'])) ]
        docker_call += [ '--stop-timeout', str(int(math.ceil(parse_time(task_spec['time'])))) ]
        assert os.path.exists(settings.OBSERVER_SOCKET)
        docker_call += [ '--volume', '{}:{}:rw'.format(settings.OBSERVER_SOCKET, settings.OBSERVER_SOCKET) ]
        docker_call += [ '--volume', '{}:{}:rw'.format(jailed_path, '/opt/kolejka') ]
        for i in [ 'kolejka-worker', 'kolejka/settings.py', 'kolejka/common.py', 'kolejka/observer/client.py', 'kolejka/observer/server.py' ]:
            os.makedirs(os.path.dirname(os.path.join(jailed_path,i)), exist_ok=True)
            with open(os.path.join(jailed_path, i), 'w') as create_file:
                pass
            docker_call += [ '--volume', '{}:{}:ro'.format(os.path.join(worker_dir_path, i), os.path.join('/opt/kolejka', i)) ]
        for key, val in task_files.items():
            docker_call += [ '--volume', '{}:{}:ro'.format(val, os.path.join('/opt/kolejka/TASK', key)) ]
        docker_call += [ '--workdir', '/opt/kolejka' ]
        docker_call += [ 'kolejka.matinf.uj.edu.pl/' + task_spec['image'] ]
        docker_call += [ '--stage', '1', 'TASK' ]

        for docker_clean in docker_cleanup:
            silent_call(docker_clean)

        subprocess.check_call(docker_call)

        result_path = os.path.join(jailed_path, 'TASK/result')
        assert os.path.isdir(result_path)
        result_spec_path = os.path.join(result_path, 'kolejka_result.json')
        assert os.path.isfile(result_spec_path)
        with open(result_spec_path, 'r') as result_spec_file:
            result_spec = json.load(result_spec_file)

        for docker_clean in docker_cleanup:
            silent_call(docker_clean)

        return_path = os.path.realpath(os.path.abspath(args.result))
        os.makedirs(return_path, exist_ok=True)
        assert os.path.isdir(return_path)
        return_spec_path = os.path.join(return_path, 'kolejka_result.json')
        with open(return_spec_path, 'w') as return_spec_file:
            print(result_spec)
            json.dump(result_spec, return_spec_file, sort_keys=True, indent=2, ensure_ascii=False)
        for file_path in result_spec['files']:
            print(file_path)
            with open(os.path.join(result_path, file_path), 'r') as file_file:
                print(file_file.read())
            os.makedirs(os.path.dirname(os.path.join(return_path, file_path)), exist_ok=True)
            shutil.move(os.path.join(result_path, file_path), os.path.join(return_path, file_path))

def stage1():
    os.makedirs(result_path, exist_ok=True)

    observer = KolejkaObserverClient()
    print(observer.post('attach'))

    with tempfile.TemporaryDirectory(dir='.') as jailed_path:
        stdin_path = '/dev/null'
        stdout_path = '/dev/null'
        stderr_path = '/dev/null'
        if 'stdin' in task_spec:
            stdin_path = os.path.join(task_path, task_spec['stdin'])
        if 'stdout' in task_spec:
            stdout_path=os.path.join(jailed_path, 'stdout')
        if 'stderr' in task_spec:
            stderr_path=os.path.join(jailed_path, 'stderr')
        with open(stdin_path, 'rb') as stdin_file:
            with open(stdout_path, 'wb') as stdout_file:
                with open(stderr_path, 'wb') as stderr_file:
                    start_time = datetime.datetime.now()
                    kwargs = dict()
                    if 'stdin' in task_spec:
                        kwargs['stdin'] = stdin_file
                    if 'stdout' in task_spec:
                        kwargs['stdout'] = stdout_file
                    if 'stderr' in task_spec:
                        kwargs['stderr'] = stderr_file
                    returncode = subprocess.call(
                        task_spec['exec'],
                        cwd=task_path,
                        **kwargs
                    )

                    stop_time = datetime.datetime.now()
        if 'stdout' in task_spec:
            stdout_new_path = os.path.join(result_path, task_spec['stdout'])
            if os.path.exists(stdout_new_path):
                os.unlink(stdout_new_path)
            os.rename(stdout_path, os.path.join(result_path, task_spec['stdout']))
        if 'stderr' in task_spec:
            stderr_new_path = os.path.join(result_path, task_spec['stderr'])
            if os.path.exists(stderr_new_path):
                os.unlink(stderr_new_path)
            os.rename(stderr_path, os.path.join(result_path, task_spec['stderr']))
        assert os.path.isdir(result_path)
        result_spec = dict()
        result_spec['stats'] = observer.post('stats')
        observer.post('close')
        result_spec['time'] = (stop_time - start_time).total_seconds()
        result_spec['id'] = task_spec['id']
        result_spec['return'] = returncode
        if os.path.exists(result_spec_path):
            os.unlink(result_spec_path)
        result_spec['files'] = list()
        for dirpath, dirnames, filenames in os.walk(result_path):
            for filename in filenames:
                abspath = os.path.join(dirpath, filename)
                if abspath.startswith(result_path+'/'):
                    relpath = abspath[len(result_path)+1:]
                    result_spec['files'].append(relpath)
        if 'stdout' in task_spec:
            result_spec['stdout'] = task_spec['stdout']
        if 'stderr' in task_spec:
            result_spec['stderr'] = task_spec['stderr']
    with open(result_spec_path, 'w') as result_spec_file:
        json.dump(result_spec, result_spec_file)
    for dirpath, dirnames, filenames in os.walk('/opt/kolejka'):
        for name in dirnames + filenames:
            abspath = os.path.join(dirpath, name)
            try:
                os.chmod(abspath, 0o777)
            except:
                pass

def main():
    if args.stage == 0:
        stage0()
    elif args.stage == 1:
        stage1()
