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

from kolejka.common.settings import OBSERVER_SOCKET, TASK_SPEC, RESULT_SPEC, WORKER_HOSTNAME, WORKER_REPOSITORY
from kolejka.common import KolejkaTask, KolejkaResult

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
        volumes.append((os.path.join(jailed_path, 'result'), '/opt/kolejka/result', 'rw'))
        for key, val in task.files.items():
            if key != TASK_SPEC:
                volumes.append((os.path.join(task.path, val.path), os.path.join('/opt/kolejka/task', key), 'ro'))
                jailed.files.add(key)
        jailed.files.add(TASK_SPEC)
        jailed.commit()
        volumes.append((jailed.spec_path, os.path.join('/opt/kolejka/task', TASK_SPEC), 'ro'))
        for spath in [ os.path.dirname(__file__) ]:
            stage1 = os.path.join(spath, 'stage1.sh')
            if os.path.isfile(stage1):
                volumes.append((stage1, '/opt/kolejka/stage1.sh', 'ro'))
                break
        for package in [ 'KolejkaCommon', 'KolejkaObserver', 'KolejkaWorker' ]:
            for spath in [ os.path.join(os.path.dirname(__file__), '../../packages/dist') ]:
                packs = glob.glob(os.path.join(spath, package+'*-py3-none-any.whl'))
                if len(packs) > 0:
                    pack = sorted(packs)[-1]
                    volumes.append((pack, '/opt/kolejka/dist/'+package+'-1-py3-none-any.whl', 'ro'))

        docker_call  = [ 'docker', 'run' ]
        docker_call += [ '--entrypoint', '/opt/kolejka/stage1.sh' ]
        for key, val in task.environment.items():
            docker_call += [ '--env', '{}={}'.format(key, val) ]
        docker_call += [ '--hostname', WORKER_HOSTNAME ]
        docker_call += [ '--init' ]
        if task.limits.memory is not None:
            docker_call += [ '--memory', str(task.limits.memory) ]
        docker_call += [ '--memory-swap', str(0) ]
        docker_call += [ '--cap-add', 'SYS_NICE' ]
        docker_call += [ '--name', docker_task ]
        if task.limits.pids is not None:
            docker_call += [ '--pids-limit', str(task.limits.pids) ]
        if task.limits.time is not None:
            docker_call += [ '--stop-timeout', str(int(math.ceil(task.limits.time.total_seconds()))) ]
        for v in volumes:
            docker_call += [ '--volume', '{}:{}:{}'.format(os.path.realpath(v[0]), v[1], v[2]) ]
        docker_call += [ '--workdir', '/opt/kolejka' ]
        docker_call += [ WORKER_REPOSITORY.rstrip('/')+ '/' + task.image ]
        docker_call += [ '--debug' ]

        for docker_clean in docker_cleanup:
            silent_call(docker_clean)

        subprocess.check_call(docker_call)

        jailed = KolejkaResult(os.path.join(jailed_path, 'result'))

        for docker_clean in docker_cleanup:
            silent_call(docker_clean)

        if os.path.exists(result_path):
            shutil.rmtree(result_path)
        os.makedirs(result_path, exist_ok=True)
        result = KolejkaResult(result_path)
        result.load(jailed.dump())
        result.files.clear()
        for key, val in jailed.files.items():
            if key != RESULT_SPEC:
                print(key)
                with open(os.path.join(jailed.path, val.path), 'r') as file_file:
                    print(file_file.read())
                os.makedirs(os.path.dirname(os.path.join(result.path, key)), exist_ok=True)
                shutil.move(os.path.join(jailed.path, val.path), os.path.join(result.path, key))
                result.files.add(key)
        result.commit()
        print(RESULT_SPEC)
        with open(result.spec_path, 'r') as file_file:
            print(file_file.read())
