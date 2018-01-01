# vim:ts=4:sts=4:sw=4:expandtab

#THIS SCRIPT MAY IMPORT ONLY STANDARD LIBRARY MODULES

import json
import logging
import os
import shutil
import subprocess
import sys
import traceback

#THIS NEEDS TO BE THE SAME AS kolejka.common.settings.TASK_SPEC
TASK_SPEC='kolejka_task.json'

def stage2(task_path, result_path):
    if not os.path.isdir(task_path):
        logging.error('Provided task path is not a directory')
        sys.exit(1)
    if not os.path.isdir(result_path):
        logging.error('Provided result path is not a directory')
        sys.exit(1)
    if os.listdir(result_path):
        logging.error('Provided result path is not emty')
        sys.exit(1)

    for dirpath, dirnames, filenames in os.walk(task_path):
        for name in dirnames + filenames:
            abspath = os.path.join(dirpath, name)
            try:
                os.chown(abspath, os.getuid(), os.getgid())
            except:
                logging.warning('Failed to chown {}'.format(abspath))
                pass
            try:
                os.chmod(abspath, 0o750)
            except:
                logging.warning('Failed to chmod {}'.format(abspath))
                pass

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

                rrp = os.path.realpath(result_path)
                trrp = os.path.realpath(os.path.join(task_path, 'result'))
                if trrp != rrp:
                    logging.debug('Creating symlink {} -> {}'.format(trrp, rrp))
                    os.symlink(rrp, trrp)
                logging.info('Executing task {} < {} > {} 2> {}'.format(task_args, task_stdin, task_stdout, task_stderr))
                result = subprocess.run(
                    args=task_args,
                    start_new_session=True,
                    cwd=task_path,
                    **kwargs
                )

                logging.info('Execution return code {}'.format(result.returncode))

    stat = os.stat(result_path)
    for dirpath, dirnames, filenames in os.walk(result_path):
        for name in dirnames + filenames:
            abspath = os.path.join(dirpath, name)
            try:
                os.chown(abspath, stat.st_uid, stat.st_gid)
            except:
                logging.warning('Failed to chown {}'.format(abspath))
                pass
        for name in dirnames:
            abspath = os.path.join(dirpath, name)
            try:
                os.chmod(abspath, 0o750)
            except:
                logging.warning('Failed to chmod {}'.format(abspath))
                pass
        for name in filenames:
            abspath = os.path.join(dirpath, name)
            try:
                os.chmod(abspath, 0o640)
            except:
                logging.warning('Failed to chmod {}'.format(abspath))
                pass

    try:
        shutil.rmtree(task_path)
    except:
        pass

    sys.exit(result.returncode)

def config_parser(parser):
    parser.add_argument("task", type=str, help='task folder')
    parser.add_argument("result", type=str, help='result folder')
    def execute(args):
        stage2(args.task, args.result)
    parser.set_defaults(execute=execute)

def main():
    import argparse
    import logging

    parser = argparse.ArgumentParser(description='KOLEJKA worker')
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help='show more info')
    parser.add_argument("-d", "--debug", action="store_true", default=False, help='show debug info')
    config_parser(parser)
    args = parser.parse_args()
    level = logging.WARNING
    if args.verbose:
        level = logging.INFO
    if args.debug:
        level = logging.DEBUG
    logging.basicConfig(level=level)
    args.execute(args)

if __name__ == '__main__':
    main()
