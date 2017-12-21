# vim:ts=4:sts=4:sw=4:expandtab

import copy
import glob
import logging
import math
import os
import shutil
import subprocess
import sys
import tempfile
import uuid

from kolejka.common.settings import OBSERVER_SOCKET, TASK_SPEC, RESULT_SPEC, WORKER_HOSTNAME, WORKER_REPOSITORY, WORKER_DIRECTORY
from kolejka.common import KolejkaTask, KolejkaResult
from kolejka.common import ControlGroupSystem

def silent_call(*args, **kwargs):
    kwargs['stdin'] = kwargs.get('stdin', subprocess.DEVNULL)
    kwargs['stdout'] = kwargs.get('stderr', subprocess.DEVNULL)
    kwargs['stderr'] = kwargs.get('stdout', subprocess.DEVNULL)
    return subprocess.call(*args, **kwargs)

def stage0(task_path, result_path, temp_path=None):
    task = KolejkaTask(task_path)
    if task.id is None:
        task.id = uuid.uuid4().hex
    assert task.image is not None
    assert len(task.args) > 0
    assert task.files.is_local
#TODO: sanitize limits (enforce some sensible max limits)

    docker_task = 'kolejka_task_{}'.format(task.id)

    docker_cleanup  = [
        [ 'docker', 'kill', docker_task ],
        [ 'docker', 'rm', docker_task ],
    ]

    with tempfile.TemporaryDirectory(dir=temp_path) as jailed_path:
        os.makedirs(os.path.join(jailed_path, 'task'), exist_ok=True)
        os.makedirs(os.path.join(jailed_path, 'result'), exist_ok=True)
        os.makedirs(os.path.join(jailed_path, 'dist'), exist_ok=True)
        jailed = KolejkaTask(os.path.join(jailed_path, 'task'))
        jailed.load(task.dump())
        jailed.files.clear()
        volumes = list()
        assert os.path.exists(OBSERVER_SOCKET)
        volumes.append((OBSERVER_SOCKET, OBSERVER_SOCKET, 'rw'))
        volumes.append((os.path.join(jailed_path, 'result'), os.path.join(WORKER_DIRECTORY, 'result'), 'rw'))
        for key, val in task.files.items():
            if key != TASK_SPEC:
                volumes.append((os.path.join(task.path, val.path), os.path.join(WORKER_DIRECTORY, 'task', key), 'ro'))
                jailed.files.add(key)
        jailed.files.add(TASK_SPEC)
        jailed.commit()
        volumes.append((jailed.spec_path, os.path.join(WORKER_DIRECTORY, 'task', TASK_SPEC), 'ro'))
        for spath in [ os.path.dirname(__file__) ]:
            stage1 = os.path.join(spath, 'stage1.sh')
            if os.path.isfile(stage1):
                volumes.append((stage1, os.path.join(WORKER_DIRECTORY, 'stage1.sh'), 'ro'))
                break
        for package in [ 'KolejkaCommon', 'KolejkaObserver', 'KolejkaWorker' ]:
            for spath in [ os.path.join(os.path.dirname(__file__), '../../packages/dist') ]:
                packs = glob.glob(os.path.join(spath, package+'*-py3-none-any.whl'))
                if len(packs) > 0:
                    pack = sorted(packs)[-1]
                    volumes.append((pack, os.path.join(WORKER_DIRECTORY, 'dist', package+'-1-py3-none-any.whl'), 'ro'))

        docker_call  = [ 'docker', 'run' ]
        docker_call += [ '--entrypoint', os.path.join(WORKER_DIRECTORY, 'stage1.sh') ]
        for key, val in task.environment.items():
            docker_call += [ '--env', '{}={}'.format(key, val) ]
        docker_call += [ '--hostname', WORKER_HOSTNAME ]
        docker_call += [ '--init' ]
        if task.limits.cpus is not None:
            cgs = ControlGroupSystem()
            docker_call += [ '--cpuset-cpus', ','.join([str(c) for c in cgs.limited_cpus(task.limits.cpus, task.limits.cpus_offset)]) ]
        if task.limits.memory is not None:
            docker_call += [ '--memory', str(task.limits.memory) ]
        if task.limits.storage is not None:
            docker_call += [ '--storage-opt', 'size='+str(task.limits.storage) ]
        if task.limits.network is not None:
            if not task.limits.network:
                docker_call += [ '--network=none' ]
        docker_call += [ '--memory-swap', str(0) ]
        docker_call += [ '--cap-add', 'SYS_NICE' ]
        docker_call += [ '--name', docker_task ]
        if task.limits.pids is not None:
            docker_call += [ '--pids-limit', str(task.limits.pids) ]
        if task.limits.time is not None:
            docker_call += [ '--stop-timeout', str(int(math.ceil(task.limits.time.total_seconds()))) ]
        for v in volumes:
            docker_call += [ '--volume', '{}:{}:{}'.format(os.path.realpath(v[0]), v[1], v[2]) ]
        docker_call += [ '--workdir', WORKER_DIRECTORY ]
        docker_call += [ WORKER_REPOSITORY.rstrip('/')+ '/' + task.image ]
        docker_call += [ '--debug' ]

        #for docker_clean in docker_cleanup:
        #    silent_call(docker_clean)

        subprocess.check_call(docker_call)

        jailed = KolejkaResult(os.path.join(jailed_path, 'result'))

        for docker_clean in docker_cleanup:
            silent_call(docker_clean)

        if os.path.exists(result_path):
            shutil.rmtree(result_path)
        os.makedirs(result_path, exist_ok=True)
        result = KolejkaResult(result_path)
        result.load(jailed.dump())
        result.id = task.id
        result.limits = task.limits
        result.stdout = task.stdout
        result.stderr = task.stderr
        result.files.clear()
        for dirpath, dirnames, filenames in os.walk(jailed.path):
            for filename in filenames:
                abspath = os.path.join(dirpath, filename)
                realpath = os.path.realpath(abspath)
                if realpath.startswith(os.path.realpath(jailed.path)+'/'):
                    relpath = abspath[len(jailed.path)+1:]
                    if relpath != RESULT_SPEC:
                        destpath = os.path.join(result.path, relpath)
                        os.makedirs(os.path.dirname(destpath), exist_ok=True)
                        shutil.move(realpath, destpath)
                        result.files.add(relpath)
                        print('#### * *')
                        print('#  '+relpath)
                        print('#### * *')
                        with open(destpath, 'r') as file_file:
                            print(file_file.read())
        result.commit()
        print(RESULT_SPEC)
        with open(result.spec_path, 'r') as file_file:
            print(file_file.read())
