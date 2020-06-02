# vim:ts=4:sts=4:sw=4:expandtab

import copy
import datetime
import dateutil.parser
import glob
import json
import logging
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

from kolejka.common.settings import OBSERVER_SOCKET, TASK_SPEC, RESULT_SPEC, WORKER_HOSTNAME, WORKER_DIRECTORY, WORKER_PYTHON_VOLUME
from kolejka.common import kolejka_config, worker_config
from kolejka.common import KolejkaTask, KolejkaResult, KolejkaLimits
from kolejka.common import ControlGroupSystem
from kolejka.common import MemoryAction, TimeAction
from kolejka.worker.volume import check_python_volume

def silent_call(*args, **kwargs):
    kwargs['stdin'] = kwargs.get('stdin', subprocess.DEVNULL)
    kwargs['stdout'] = kwargs.get('stderr', subprocess.DEVNULL)
    kwargs['stderr'] = kwargs.get('stdout', subprocess.DEVNULL)
    return subprocess.run(*args, **kwargs)

def stage0(task_path, result_path, temp_path=None, consume_task_folder=False):
    config = worker_config()
    cgs = ControlGroupSystem()
    task = KolejkaTask(task_path)
    if not task.id:
        task.id = uuid.uuid4().hex
        logging.warning('Assigned id {} to the task'.format(task.id))
    if not task.image:
        logging.error('Task does not define system image')
        sys.exit(1)
    if not task.args:
        logging.error('Task does not define args')
        sys.exit(1)
    if not task.files.is_local:
        logging.error('Task contains non-local files')
        sys.exit(1)
    limits = KolejkaLimits()
    limits.cpus = config.cpus
    limits.memory = config.memory
    limits.swap = config.swap
    limits.pids = config.pids
    limits.storage = config.storage
    limits.image = config.image
    limits.workspace = config.workspace
    limits.time = config.time
    limits.network = config.network
    task.limits.update(limits)

    docker_task = 'kolejka_worker_{}'.format(task.id)

    docker_cleanup  = [
        [ 'docker', 'kill', docker_task ],
        [ 'docker', 'rm', docker_task ],
    ]

    with tempfile.TemporaryDirectory(dir=temp_path) as jailed_path:
#TODO jailed_path size remains unlimited?
        logging.debug('Using {} as temporary directory'.format(jailed_path))
        jailed_task_path = os.path.join(jailed_path, 'task')
        os.makedirs(jailed_task_path, exist_ok=True)
        jailed_result_path = os.path.join(jailed_path, 'result')
        os.makedirs(jailed_result_path, exist_ok=True)

        jailed = KolejkaTask(os.path.join(jailed_path, 'task'))
        jailed.load(task.dump())
        jailed.files.clear()
        volumes = list()
        check_python_volume()
        if os.path.exists(OBSERVER_SOCKET):
            volumes.append((OBSERVER_SOCKET, OBSERVER_SOCKET, 'rw'))
        else:
            logging.warning('Observer is not running.')
        volumes.append((jailed_result_path, os.path.join(WORKER_DIRECTORY, 'result'), 'rw'))
        for key, val in task.files.items():
            if key != TASK_SPEC:
                src_path = os.path.join(task.path, val.path)
                dst_path = os.path.join(jailed_path, 'task', key)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                if consume_task_folder:
                    shutil.move(src_path, dst_path)
                else:
                    shutil.copy(src_path, dst_path)
                jailed.files.add(key)
        jailed.files.add(TASK_SPEC)
        #jailed.limits = KolejkaLimits() #TODO: Task is limited by docker, no need to limit it again?
        jailed.commit()
        volumes.append((jailed.path, os.path.join(WORKER_DIRECTORY, 'task'), 'rw'))
        if consume_task_folder:
            try:
                shutil.rmtree(task_path)
            except:
                logging.warning('Failed to remove {}'.format(task_path))
                pass
        for spath in [ os.path.dirname(__file__) ]:
            stage1 = os.path.join(spath, 'stage1.sh')
            if os.path.isfile(stage1):
                volumes.append((stage1, os.path.join(WORKER_DIRECTORY, 'stage1.sh'), 'ro'))
                break
        for spath in [ os.path.dirname(__file__) ]:
            stage2 = os.path.join(spath, 'stage2.py')
            if os.path.isfile(stage2):
                volumes.append((stage2, os.path.join(WORKER_DIRECTORY, 'stage2.py'), 'ro'))
                break

        docker_call  = [ 'docker', 'run' ]
        docker_call += [ '--detach' ]
        docker_call += [ '--name', docker_task ]
        docker_call += [ '--entrypoint', os.path.join(WORKER_DIRECTORY, 'stage1.sh') ]
        for key, val in task.environment.items():
            docker_call += [ '--env', '{}={}'.format(key, val) ]
        docker_call += [ '--hostname', WORKER_HOSTNAME ]
        docker_call += [ '--init' ]
        if task.limits.cpus is not None:
            docker_call += [ '--cpuset-cpus', ','.join([str(c) for c in cgs.limited_cpuset(cgs.full_cpuset(), task.limits.cpus, task.limits.cpus_offset)]) ]
        if task.limits.memory is not None:
            docker_call += [ '--memory', str(task.limits.memory) ]
            if task.limits.swap is not None:
                docker_call += [ '--memory-swap', str(task.limits.memory + task.limits.swap) ]
        if task.limits.storage is not None:
            docker_info_run = subprocess.run(['docker', 'system', 'info', '--format', '{{json .Driver}}'], stdout=subprocess.PIPE, check=True)
            storage_driver = str(json.loads(str(docker_info_run.stdout, 'utf-8')))
            if storage_driver == 'overlay2':
                docker_info_run = subprocess.run(['docker', 'system', 'info', '--format', '{{json .DriverStatus}}'], stdout=subprocess.PIPE, check=True)
                storage_fs = dict(json.loads(str(docker_info_run.stdout, 'utf-8')))['Backing Filesystem']
                if storage_fs in [ 'xfs' ]:
                    storage_limit = task.limits.storage
                    docker_call += [ '--storage-opt', 'size='+str(storage_limit) ]
                else:
                    logging.warning("Storage limit on {} ({}) is not supported".format(storage_driver, storage_fs))
            else:
                logging.warning("Storage limit on {} is not supported".format(storage_driver))
        if task.limits.network is not None:
            if not task.limits.network:
                docker_call += [ '--network=none' ]
        docker_call += [ '--cap-add', 'SYS_NICE' ]
        if task.limits.pids is not None:
            docker_call += [ '--pids-limit', str(task.limits.pids) ]
        if task.limits.time is not None:
            docker_call += [ '--stop-timeout', str(int(math.ceil(task.limits.time.total_seconds()))) ]
        docker_call += [ '--volume', '{}:{}:{}'.format(WORKER_PYTHON_VOLUME, os.path.join(WORKER_DIRECTORY, 'python3'), 'ro') ]
        for v in volumes:
            docker_call += [ '--volume', '{}:{}:{}'.format(os.path.realpath(v[0]), v[1], v[2]) ]
        docker_call += [ '--workdir', WORKER_DIRECTORY ]
        docker_image = task.image
        docker_call += [ docker_image ]
        docker_call += [ '--consume' ]
        if config.debug:
            docker_call += [ '--debug' ]
        if config.verbose:
            docker_call += [ '--verbose' ]
        docker_call += [ os.path.join(WORKER_DIRECTORY, 'task') ]
        docker_call += [ os.path.join(WORKER_DIRECTORY, 'result') ]
        logging.debug('Docker call : {}'.format(docker_call))

        pull_image = config.pull
        if not pull_image:
            docker_inspect_run = subprocess.run(['docker', 'image', 'inspect', docker_image], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            if docker_inspect_run.returncode != 0:
                pull_image = True 
        if pull_image:
            subprocess.run(['docker', 'pull', docker_image], check=True)

        for docker_clean in docker_cleanup:
            silent_call(docker_clean)

        if os.path.exists(result_path):
            shutil.rmtree(result_path)
        os.makedirs(result_path, exist_ok=True)
        result = KolejkaResult(result_path)
        result.id = task.id
        result.limits = task.limits
        result.stdout = task.stdout
        result.stderr = task.stderr

        start_time = datetime.datetime.now()
        docker_run = subprocess.run(docker_call, stdout=subprocess.PIPE)
        cid = str(docker_run.stdout, 'utf-8').strip()
        logging.info('Started container {}'.format(cid))

        while True:
            try:
                docker_state_run = subprocess.run(['docker', 'inspect', '--format', '{{json .State}}', cid], stdout=subprocess.PIPE)
                state = json.loads(str(docker_state_run.stdout, 'utf-8'))
            except:
                break
            try:
                result.stats.update(cgs.name_stats(cid))
            except:
                pass
            time.sleep(0.1)
            if not state['Running']:
                result.result = state['ExitCode']
                try:
                    result.stats.time = dateutil.parser.parse(state['FinishedAt']) - dateutil.parser.parse(state['StartedAt'])
                except:
                    result.stats.time = None
                break
            if task.limits.time is not None and datetime.datetime.now() - start_time > task.limits.time + datetime.timedelta(seconds=2):
                docker_kill_run = subprocess.run([ 'docker', 'kill', docker_task ])
        subprocess.run(['docker', 'logs', cid], stdout=subprocess.PIPE)
        try:
            summary = KolejkaResult(jailed_result_path)
            result.stats.update(summary.stats)
        except:
            pass

        stop_time = datetime.datetime.now()
        if result.stats.time is None:
            result.stats.time = stop_time - start_time
        result.stats.pids.usage = None
        result.stats.memory.usage = None
        result.stats.memory.swap = None

        for dirpath, dirnames, filenames in os.walk(jailed_result_path):
            for filename in filenames:
                abspath = os.path.join(dirpath, filename)
                realpath = os.path.realpath(abspath)
                if realpath.startswith(os.path.realpath(jailed_result_path)+'/'):
                    relpath = abspath[len(jailed_result_path)+1:]
                    if relpath != RESULT_SPEC:
                        destpath = os.path.join(result.path, relpath)
                        os.makedirs(os.path.dirname(destpath), exist_ok=True)
                        shutil.move(realpath, destpath)
                        os.chmod(destpath, 0o640)
                        result.files.add(relpath)
        result.commit()
        os.chmod(result.spec_path, 0o640)

        for docker_clean in docker_cleanup:
            silent_call(docker_clean)

def config_parser(parser):
    parser.add_argument("task", type=str, help='task folder')
    parser.add_argument("result", type=str, help='result folder')
    parser.add_argument("--temp", type=str, help='temp folder')
    parser.add_argument('--pull', action='store_true', help='always pull images, even if local version is present', default=False)
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
        config = worker_config()
        stage0(args.task, args.result, temp_path=config.temp_path, consume_task_folder=args.consume)
    parser.set_defaults(execute=execute)
