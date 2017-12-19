# vim:ts=4:sts=4:sw=4:expandtab

import datetime
import os
import shutil
import subprocess
import sys
import tempfile

from kolejka.common import settings
from kolejka.common import KolejkaTask, KolejkaResult
from kolejka.observer.client import KolejkaObserverClient

def stage2(task_path, result_path):
    task = KolejkaTask(task_path)
    result = KolejkaResult(result_path)
    os.makedirs(result.path, exist_ok=True)

    observer = KolejkaObserverClient()
    print(observer.post('attach'))
    limits = dict()
    if task.cpus is not None:
        limits['cpus'] = task.cpus
    if task.memory is not None:
        limits['memory'] = task.memory
    if task.pids is not None:
        limits['pids'] = task.pids
    #TODO:cpu_offset
    print(observer.post('limit', limits ))

    with tempfile.TemporaryDirectory(dir='.') as jailed_path:
        stdin_path = '/dev/null'
        stdout_path = '/dev/null'
        stderr_path = '/dev/null'
        if task.stdin is not None:
            stdin_path = os.path.join(task.path, task.stdin)
        if task.stdout is not None:
            stdout_path=os.path.join(jailed_path, 'stdout')
        if task.stderr is not None:
            stderr_path=os.path.join(jailed_path, 'stderr')
        with open(stdin_path, 'rb') as stdin_file:
            with open(stdout_path, 'wb') as stdout_file:
                with open(stderr_path, 'wb') as stderr_file:
                    start_time = datetime.datetime.now()
                    kwargs = dict()
                    if task.stdin is not None:
                        kwargs['stdin'] = stdin_file
                    if task.stdout is not None:
                        kwargs['stdout'] = stdout_file
                    if task.stderr is not None:
                        kwargs['stderr'] = stderr_file
                    returncode = subprocess.call(
                        args=task.args,
                        **kwargs
                    )

                    stop_time = datetime.datetime.now()
        if task.stdout is not None:
            stdout_new_path = os.path.join(result.path, task.stdout)
            if os.path.exists(stdout_new_path):
                os.unlink(stdout_new_path)
            shutil.move(stdout_path, stdout_new_path)
        if task.stderr is not None:
            stderr_new_path = os.path.join(result.path, task.stderr)
            if os.path.exists(stderr_new_path):
                os.unlink(stderr_new_path)
            shutil.move(stderr_path, stderr_new_path)
        assert os.path.isdir(result.path)
        result.id = task.id
        result.stats = observer.post('stats')
        observer.post('close')
        result.time = (stop_time - start_time).total_seconds()
        result.result = returncode
        for dirpath, dirnames, filenames in os.walk(result.path):
            for filename in filenames:
                abspath = os.path.join(dirpath, filename)
                if abspath.startswith(result.path+'/'):
                    relpath = abspath[len(result.path)+1:]
                    result.add_file(relpath)
        if task.stdout is not None:
            result.stdout = task.stdout
        if task.stderr is not None:
            result.stderr = task.stderr
        result.commit()

    for dirpath, dirnames, filenames in os.walk('/opt/kolejka'):
        for name in dirnames + filenames:
            abspath = os.path.join(dirpath, name)
            try:
                os.chmod(abspath, 0o777)
            except:
                pass

