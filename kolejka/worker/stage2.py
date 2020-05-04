# vim:ts=4:sts=4:sw=4:expandtab

#THIS SCRIPT MAY IMPORT ONLY STANDARD LIBRARY MODULES

import argparse
import datetime
import glob
import http.client
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import traceback

#THIS NEEDS TO BE THE SAME AS kolejka.common.settings.TASK_SPEC
TASK_SPEC='kolejka_task.json'

#THIS NEEDS TO BE THE SAME AS kolejka.common.settings.RESULT_SPEC
RESULT_SPEC='kolejka_result.json'

#THIS NEEDS TO BE THE SAME AS kolejka.common.settings.OBSERVER_SOCKET
OBSERVER_SOCKET = "/var/run/kolejka/observer/socket"

def parse_float_with_modifiers(x, modifiers):
    if isinstance(x, float):
        return x
    if isinstance(x, int):
        return float(x)
    modifier = 1
    x = str(x).strip()
    while len(x) > 0 and x[-1] in modifiers :
        modifier *= modifiers[x[-1]]
        x = x[:-1]
    return float(x) * modifier

def parse_int(x):
    if x is not None:
        return int(x)

def parse_memory(x):
    if x is not None:
        return int(round(parse_float_with_modifiers(x, {
            'b' : 1,
            'B' : 1,
            'k' : 1024,
            'K' : 1024,
            'm' : 1024**2,
            'M' : 1024**2,
            'g' : 1024**3,
            'G' : 1024**3,
            't' : 1024**4,
            'T' : 1024**4,
            'p' : 1024**5,
            'P' : 1024**5,
        })))

def parse_time(x) :
    if x is not None:
        if isinstance(x, datetime.timedelta):
            return x
        return datetime.timedelta(seconds=parse_float_with_modifiers(x, {
            'D' : 60**2*24,
            'H' : 60**2,
            'M' : 60,
            's' : 1,
            'm' : 10**-3,
            'µ' : 10**-6,
            'n' : 10**-9,
        }))

class MemoryAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self.type = int
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super().__init__(option_strings, dest, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, parse_memory(values))

class TimeAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self.type = datetime.timedelta
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super().__init__(option_strings, dest, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, parse_time(values))

class HTTPUnixConnection(http.client.HTTPConnection):
    def _get_hostport(self, host, port):
        return (self.socket_path, None)
    def __init__(self, socket_path):
        self.socket_path = socket_path
        super().__init__(self, socket_path)
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)
        if self._tunnel_host:
            self._tunnel()

def observer_start(cpus, cpus_offset, memory, swap, pids, time):
    if not os.path.exists(OBSERVER_SOCKET):
        logging.error('Limits enabled with no kolejka-observer socket present')
        sys.exit(0)
    conn = HTTPUnixConnection(OBSERVER_SOCKET)
    headers = dict()
    headers['Content-Type'] = 'application/json; charset=utf-8'
    headers['Content-Length'] = '2'
    conn.request('POST', 'attach', '{}', headers)
    with conn.getresponse() as response:
        response_body = json.loads(response.read().decode('utf-8'))
    session_id = response_body['session_id']
    secret = response_body['secret']
    if cpus is not None or memory is not None or swap is not None or pids is not None: 
        limits = dict()
        if cpus is not None:
            limits['cpus'] = int(cpus)
        if cpus_offset is not None:
            limits['cpus_offset'] = int(cpus_offset)
        if memory is not None:
            limits['memory'] = int(memory)
        if swap is not None:
            limits['swap'] = int(swap)
        if pids is not None:
            limits['pids'] = int(pids)
        if time is not None:
            limits['time'] = float(time.total_seconds()) 
        params = dict()
        params['limits'] = limits
        params['session_id'] = session_id
        params['secret'] = secret
        body = bytes(json.dumps(params), 'utf-8')
        headers['Content-Length'] = str(len(body))
        conn.request('POST', 'limits', body, headers)
        with conn.getresponse() as response:
            response_body = json.loads(response.read().decode('utf-8'))
    conn.close()
    return session_id, secret

def observer_stop(session_id, secret):
    if not os.path.exists(OBSERVER_SOCKET):
        logging.error('Limits enabled with no kolejka-observer socket present')
        sys.exit(0)
    conn = HTTPUnixConnection(OBSERVER_SOCKET)
    headers = dict()
    headers['Content-Type'] = 'application/json; charset=utf-8'
    params = dict()
    params['session_id'] = session_id
    params['secret'] = secret
    body = bytes(json.dumps(params), 'utf-8')
    headers['Content-Length'] = str(len(body))
    conn.request('POST', 'stats', body, headers)
    with conn.getresponse() as response:
        response_body = json.loads(response.read().decode('utf-8'))
    conn.request('POST', 'detach', body, headers)
    conn.getresponse()
    conn.request('POST', 'close', body, headers)
    conn.getresponse()
    conn.close()
    return response_body

def stage2(task_path, result_path, consume, cpus=None, cpus_offset=None, memory=None, swap=None, pids=None, time=None):
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

    task = dict()
    task_spec_path = os.path.join(task_path, TASK_SPEC)
    with open(task_spec_path) as task_spec_file:
        task = json.load(task_spec_file)
    task_stdin = task.get('stdin', None)
    task_stdout = task.get('stdout', None)
    task_stderr = task.get('stderr', None)
    task_args = task.get('args', [ 'true' ])
    task_cpus = parse_int(task.get('limits', dict()).get('cpus', None))
    task_cpus_offset = parse_int(task.get('limits', dict()).get('cpus_offset', None))
    task_memory = parse_memory(task.get('limits', dict()).get('memory', None))
    task_swap = parse_memory(task.get('limits', dict()).get('swap', None))
    task_pids = parse_int(task.get('limits', dict()).get('pids', None))
    task_time = parse_time(task.get('limits', dict()).get('time', None))
    task_env = task.get('environment', dict())

    if task_cpus is not None and (cpus is None or task_cpus < cpus):
        cpus = task_cpus
    if task_cpus_offset is not None and (cpus_offset is None):
        cpus_offset = task_cpus_offset
    if task_memory is not None and (memory is None or task_memory < memory):
        memory = task_memory
    if task_swap is not None and (swap is None or task_swap < swap):
        swap = task_swap
    if task_pids is not None and (pids is None or task_pids < pids):
        pids = task_pids
    if task_time is not None and (time is None or task_time.total_seconds() < time.total_seconds()):
        time = task_time
    
    summary = dict()
    summary['files'] = dict()
    summary_spec_path = os.path.join(result_path, RESULT_SPEC)
    for field in [ 'id', 'stdout', 'stderr' ]:
        if field in task:
            summary[field] = task[field]
    summary['limits'] = dict()
    if cpus is not None:
        summary['limits']['cpus'] = cpus
    if cpus_offset is not None:
        summary['limits']['cpus_offset'] = cpus_offset
    if memory is not None:
        summary['limits']['memory'] = memory
    if swap is not None:
        summary['limits']['swap'] = swap
    if pids is not None:
        summary['limits']['pids'] = pids
    if time is not None:
        summary['limits']['time'] = time.total_seconds()

    observer = None
    if os.path.exists(OBSERVER_SOCKET):
        observer = observer_start(cpus, cpus_offset, memory, swap, pids, time)
        logging.info('Using Kolejka Observer to limit task and collect stats.')
    else:
        if cpus is not None or memory is not None or swap is not None or pids is not None or time is not None:
            logging.error('Can\'t limit task without Kolejka Observer running.')
            sys.exit(1)

    stdin_path = '/dev/null'
    stdout_path = '/dev/stdout'
    stderr_path = '/dev/stderr'
    if task_stdin is not None:
        stdin_path = os.path.join(task_path, task_stdin)
    if task_stdout is not None:
        stdout_path = os.path.join(result_path, task_stdout)
        summary['files'][task_stdout] = dict()
        summary['files'][task_stdout]['path'] = task_stdout
    if task_stderr is not None:
        if task_stderr != task_stdout:
            stderr_path = os.path.join(result_path, task_stderr)
            summary['files'][task_stderr] = dict()
            summary['files'][task_stderr]['path'] = task_stderr

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
                env = dict()
                env['IFS'] = ' '
                env['PATH'] = '/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin'
                env['PWD'] = task_path
                env['USER'] = 'root'
                env['HOME'] = task_path
                env.update(task_env)
                logging.info('Executing task {} < {} > {} 2> {} (Env: {})'.format(task_args, task_stdin, task_stdout, task_stderr, env))
                result = subprocess.run(
                    args=task_args,
                    start_new_session=True,
                    cwd=task_path,
                    env=env,
                    **kwargs
                )
                logging.info('Execution return code {}'.format(result.returncode))
    if observer:
        summary['stats'] = observer_stop(*observer)
    summary['result'] = result.returncode

    orig_path = os.getcwd()
    os.chdir(task_path)
    collects = list()
    for collect in task.get('collect', []):
        collect_glob = str(collect.get('glob'))
        collect_strip = int(collect.get('strip', 0))
        collect_prefix = str(collect.get('prefix', ''))
        for f in glob.iglob(collect_glob, recursive=True):
            if os.path.isfile(f):
                collects.append(( os.path.islink(f), f, collect_strip, collect_prefix ))
    for is_link, f, collect_strip, collect_prefix in sorted(collects, reverse=True):
                split = f.strip('/').split('/')
                split = split[min(collect_strip, len(split)-1):]
                strip = '/'.join(split)
                strip = os.path.join(collect_prefix.strip('/'), strip)
                dest = os.path.join(result_path, strip)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                if is_link:
                    shutil.copy(os.path.realpath(f), dest)
                elif consume:
                    shutil.move(f, dest)
                else:
                    shutil.copy(f, dest)
                summary['files'][strip] = dict()
                summary['files'][strip]['path'] = strip
    os.chdir(orig_path)

    with open(summary_spec_path, 'w') as summary_spec_file:
        json.dump(summary, summary_spec_file, sort_keys=True, indent=2, ensure_ascii=False)

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

    if consume:
        for entry in os.listdir(task_path):
            try:
                entry = os.path.join(task_path, entry)
                if os.path.islink(entry) or os.path.isfile(entry):
                    os.unlink(entry)
                elif os.path.isdir(entry):
                    shutil.rmtree(entry)
            except:
                pass

    sys.exit(result.returncode)

def config_parser(parser):
    parser.add_argument("task", type=str, help='task folder')
    parser.add_argument("result", type=str, help='result folder')
    parser.add_argument("--consume", action="store_true", default=False, help='consume task folder') 
    parser.add_argument('--cpus', type=int, help='cpus limit')
    parser.add_argument('--cpus-offset', type=int, help='cpus limit')
    parser.add_argument('--memory', action=MemoryAction, help='memory limit')
    parser.add_argument('--swap', action=MemoryAction, help='swap limit')
    parser.add_argument('--pids', type=int, help='pids limit')
    parser.add_argument('--time', action=TimeAction, help='time limit')
    def execute(args):
        stage2(args.task, args.result, args.consume, cpus=args.cpus, cpus_offset=args.cpus_offset, memory=args.memory, swap=args.swap, pids=args.pids, time=args.time)
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
