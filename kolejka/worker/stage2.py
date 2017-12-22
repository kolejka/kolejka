# vim:ts=4:sts=4:sw=4:expandtab

import datetime
import json
import logging
import os
import subprocess
import sys

#THIS NEEDS TO BE THE SAME AS kolejka.common.settings.TASK_SPEC
TASK_SPEC='kolejka_task.json'

def stage2(task_path, result_path):

    os.makedirs(result_path, exist_ok=True)

    task = {}
    task_spec_path = os.path.join(task_path, TASK_SPEC)
    with open(task_spec_path) as task_spec_file:
        task = json.load(task_spec_file)
    task_stdin = task.get('stdin', None)
    task_stdout = task.get('stdout', None)
    task_stderr = task.get('stderr', None)
    task_args = task.get('args', [ 'true' ])

    stdin_path = '/dev/null'
    stdout_path = '/dev/null'
    stderr_path = '/dev/null'
    if task_stdin is not None:
        stdin_path = os.path.join(task_path, task_stdin)
    if task_stdout is not None:
        stdout_path = os.path.join(result_path, task_stdout)
    if task_stderr is not None:
        if task_stderr != task_stdout:
            stderr_path = os.path.join(result_path, task_stderr)
    with open(stdin_path, 'rb') as stdin_file:
        with open(stdout_path, 'wb') as stdout_file:
            with open(stderr_path, 'wb') as stderr_file:
                kwargs = dict()
                if task_stdin is not None:
                    kwargs['stdin'] = stdin_file
                if task_stdout is not None:
                    kwargs['stdout'] = stdout_file
                if task_stderr is not None:
                    if task_stderr != task_stdout:
                        kwargs['stderr'] = stderr_file
                    else:
                        kwargs['stderr'] = subprocess.STDOUT

                result = subprocess.run(
                    args=task_args,
                    start_new_session=True,
                    **kwargs
                )

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

    sys.exit(result.returncode)

if __name__ == '__main__':
    stage2(sys.argv[1], sys.argv[2])
