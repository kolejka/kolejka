# vim:ts=4:sts=4:sw=4:expandtab

import copy
import glob
import math
import os
import shutil
import subprocess
import sys
import tempfile
import uuid

from kolejka.common import settings
from kolejka.common import silent_call
from kolejka.common import KolejkaTask, KolejkaResult

def stage0(task_path, result_path, temp_path=None):
    task = KolejkaTask(task_path)
#    if task.id is None:
#        task.id = uuid.uuid4().hex
#        task.commit()
    print(task.id, task.args, task.files)
    docker_task = 'kolejka_task_{}'.format(task.id)

    docker_cleanup  = [
        [ 'docker', 'kill', docker_task ],
        [ 'docker', 'rm', docker_task ],
    ]

    with tempfile.TemporaryDirectory(dir=temp_path) as jailed_path:
        os.makedirs(os.path.join(jailed_path, 'task'), exist_ok=True)
        os.makedirs(os.path.join(jailed_path, 'result'), exist_ok=True)
        os.makedirs(os.path.join(jailed_path, 'dist'), exist_ok=True)
        volumes = list()
        volumes.append((settings.OBSERVER_SOCKET, settings.OBSERVER_SOCKET, 'rw'))
        volumes.append((os.path.join(jailed_path, 'result'), '/opt/kolejka/result', 'rw'))
        for key, val in task.files.items():
            if key != settings.TASK_SPEC:
                volumes.append((os.path.join(task.path, val.path), os.path.join('/opt/kolejka/task', key), 'ro'))
        volumes.append((task.spec_path, os.path.join('/opt/kolejka/task', settings.TASK_SPEC), 'ro'))
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
        print(volumes)

        docker_call  = [ 'docker', 'run' ]
#        docker_call += [ '--cgroup-parent', docker_task ]
#        docker_call += [ '--cpus', str(task.cpus) ]
#        for device in task.devices :
#            docker_call += [ '--device', device ]
        docker_call += [ '--entrypoint', '/opt/kolejka/stage1.sh' ]
        for key, val in task.environment.items():
            docker_call += [ '--env', '{}={}'.format(key, val) ]
        docker_call += [ '--hostname', 'kolejka' ]
        docker_call += [ '--init' ]
        docker_call += [ '--memory', str(task.memory) ]
        docker_call += [ '--memory-swap', str(0) ]
        docker_call += [ '--cap-add', 'SYS_NICE' ]
        docker_call += [ '--name', docker_task ]
        docker_call += [ '--pids-limit', str(task.pids) ]
        docker_call += [ '--stop-timeout', str(int(math.ceil(task.time))) ]
        assert os.path.exists(settings.OBSERVER_SOCKET)
        for v in volumes:
            docker_call += [ '--volume', '{}:{}:{}'.format(os.path.realpath(v[0]), v[1], v[2]) ]
        docker_call += [ '--workdir', '/opt/kolejka' ]
        docker_call += [ 'kolejka.matinf.uj.edu.pl/' + task.image ]
        docker_call += [ '--debug' ]

        for docker_clean in docker_cleanup:
            silent_call(docker_clean)

        print(docker_call)

        subprocess.check_call(docker_call)


        result = KolejkaResult(os.path.join(jailed_path, 'result'))

        for docker_clean in docker_cleanup:
            silent_call(docker_clean)

        os.makedirs(result_path, exist_ok=True)
        reresult = KolejkaResult(result_path)
        reresult.spec = copy.copy(result.spec)
        for key, val in result.files.items():
            print(key)
            with open(os.path.join(result.path, val.path), 'r') as file_file:
                print(file_file.read())
            os.makedirs(os.path.dirname(os.path.join(reresult.path, key)), exist_ok=True)
            shutil.move(os.path.join(result.path, val.path), os.path.join(reresult.path, key))
            reresult.add_file(key)
        reresult.commit()

def main():
    import argparse
    import logging
    import setproctitle

    parser = argparse.ArgumentParser(description='KOLEJKA worker')
    parser.add_argument("-t", "--task", type=str, default='TASK', help='task folder')
    parser.add_argument("-r", "--result", type=str, default='RESULT', help='result folder')
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help='show more info')
    parser.add_argument("-d", "--debug", action="store_true", default=False, help='show debug info')
    parser.add_argument("--temp", type=str, default=None, help='temporary directory')
    args = parser.parse_args()
    level=logging.WARNING
    if args.verbose:
        level=logging.INFO
    if args.debug:
        level=logging.DEBUG
    logging.basicConfig(level=level)
    setproctitle.setproctitle('kolejka-worker')
    stage0(args.task, args.result, args.temp)

if __name__ == '__main__':
    main()
