# vim:ts=4:sts=4:sw=4:expandtab

import datetime
import logging
import os
import shutil
import subprocess
import sys
import tempfile

from kolejka.common import KolejkaTask, KolejkaResult
from kolejka.observer.client import KolejkaObserverClient

def stage2(task_path, result_path):
    task = KolejkaTask(task_path)
    result = KolejkaResult(result_path)
    os.makedirs(result.path, exist_ok=True)

    observer = KolejkaObserverClient()
    observer.attach()
    observer.limits(task.limits)

    stdin_path = '/dev/null'
    stdout_path = '/dev/null'
    stderr_path = '/dev/null'
    if task.stdin is not None:
        stdin_path = os.path.join(task.path, task.stdin)
    if task.stdout is not None:
        stdout_path=os.path.join(result.path, task.stdout)
    if task.stderr is not None:
        stderr_path=os.path.join(result.path, task.stderr)
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

    result.stats = observer.stats()
    observer.close()

    result.stats.time = stop_time - start_time
    result.result = returncode
    result.commit()

    stat = os.stat(result_path)
    for dirpath, dirnames, filenames in os.walk(result_path):
        for name in dirnames + filenames:
            abspath = os.path.join(dirpath, name)
            try:
                os.chown(abspath, stat.st_uid, stat.st_gid)
            except:
                pass
        for name in dirnames:
            abspath = os.path.join(dirpath, name)
            try:
                os.chmod(abspath, 0o750)
            except:
                pass
        for name in filenames:
            abspath = os.path.join(dirpath, name)
            try:
                os.chmod(abspath, 0o640)
            except:
                pass
