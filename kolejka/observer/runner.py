# vim:ts=4:sts=4:sw=4:expandtab

import io
import json
import logging
import os
import pathlib
import subprocess
import sys
import threading

from kolejka.common import settings
from kolejka.common import KolejkaLimits
from kolejka.common import MemoryAction, TimeAction
import kolejka.common.subprocess
from kolejka.observer.client import KolejkaObserverClient

class CompletedProcess(kolejka.common.subprocess.CompletedProcess):
    def __init__(self, *args, stats, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = stats
    @property
    def limits(self):
        return self.starter.limits

class Starter(kolejka.common.subprocess.Starter):
    def __init__(self, *args, limits=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.limits = limits

    def get_imports(self):
        imports = super().get_imports()
        imports.add('socket')
        return imports

    def get_commands(self):
        commands = list()
        session_id = self.session['session_id']
        secret = self.session['secret']
        data = bytes(json.dumps(self.session), 'utf8')
        request = b'\r\n'.join([
        b'POST /attach HTTP/1.1',
        b'Host: kolejka-observer',
        b'Content-Type: application/json; charset=utf-8',
        b'Content-Length: '+bytes(str(len(data)),'utf8'),
        b'',
        data,
        ])

        commands.append('with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:')
        commands.append('  sock.connect({})'.format(self.represent(settings.OBSERVER_SOCKET)))
        commands.append('  sock.sendall({})'.format(self.represent(request)))
        commands.append('  sock.recv(1024)')
        commands += super().get_commands()
        return commands

    def __call__(self, *args, **kwargs):
        self.client = KolejkaObserverClient()
        self.session = self.client.open()
        if self.limits:
            self.client.limits(self.limits)
        return super().__call__(*args, **kwargs)

    def __del__(self):
        try:
            self.client.close()
        except:
            pass

def start(*args, _Starter=Starter, **kwargs):
    return kolejka.common.subprocess.start(*args, _Starter=_Starter, **kwargs)

def wait(process, input=None, timeout=None, check=False):
    result = kolejka.common.subprocess.wait(process, input=input, timeout=timeout, check=check)
    return CompletedProcess(starter=result.starter, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr, time=result.time, stats=result.starter.client.stats())

def run(*args, _Starter=Starter, **kwargs):
    result = kolejka.common.subprocess.run(*args, _Starter=_Starter, **kwargs)
    return CompletedProcess(starter=result.starter, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr, time=result.time, stats=result.starter.client.stats())

def file_reader(path):
    return pathlib.Path(path).open('rb')
def file_writer(path, append =False, max_bytes =None):
    path = pathlib.Path(path)
    path.parent.mkdir(exist_ok=True, parents=True)
    mode = 'wb'
    if append:
        mode += 'a'
    fd_read, fd_write = os.pipe()
    def writer():
        bytes = 0
        with path.open(mode) as output:
            while True:
                data = os.read(fd_read, 65536)
                if not data:
                    break
                if max_bytes is not None:
                    if bytes < max_bytes:
                        data = data[0:max_bytes-bytes]
                    else:
                        data = b''
                bytes += len(data)
                output.write(data)
        os.close(fd_read)
    w = threading.Thread(target=writer)
    w.start()
    return (io.FileIO(fd_write, mode='wb', closefd=True), w)


def main():
    import argparse
    import daemon
    import grp
    import logging
    import os
    import pwd

    parser = argparse.ArgumentParser(description='KOLEJKA runner')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='show more info')
    parser.add_argument('-d', '--debug', action='store_true', default=False, help='show debug info')
    parser.add_argument('--stdin', help='redirect stdin')
    parser.add_argument('--stdout', help='redirect stdout')
    parser.add_argument('--stdout-append', action='store_true', default=False, help='append stdout file')
    parser.add_argument('--stdout-max-bytes', type=int, help='stdout maximum length')
    parser.add_argument('--stderr', help='redirect stderr')
    parser.add_argument('--stderr-append', action='store_true', default=False, help='append stderr file')
    parser.add_argument('--stderr-max-bytes', type=int, help='stderr maximum length')
    parser.add_argument('--root', help='root directory')
    parser.add_argument('--dir', help='work directory')
    parser.add_argument('--clear-env', action='store_true', default=False, help='clear environment')
    parser.add_argument('--env', action='append', default=list(), help='define environment variable VAR=VAL')
    parser.add_argument('--session', action='store_true', default=False, help='start new session')
    parser.add_argument('--background', action='store_true', default=False, help='run in background')
    parser.add_argument('--pid-file', help='detach process')
    parser.add_argument('--stats-file', help='store statistics in a file')
    parser.add_argument('--user', help='change uid')
    parser.add_argument('--group', help='change gid')
    parser.add_argument('--groups', help='change groups')
    parser.add_argument('--umask', help='change umask')
    parser.add_argument('--nice', help='change nice level')

    parser.add_argument('--cpus', type=int, help='cpus limit')
    parser.add_argument('--cpus-offset', type=int, help='cpus limit')
    parser.add_argument('--memory', action=MemoryAction, help='memory limit')
    parser.add_argument('--swap', action=MemoryAction, help='swap limit')
    parser.add_argument('--pids', type=int, help='pids limit')
    parser.add_argument('--time', action=TimeAction, help='time limit')
    parser.add_argument('args', nargs=argparse.REMAINDER, help='command line to run')
    args = parser.parse_args()
    level=logging.WARNING
    if args.verbose:
        level=logging.INFO
    if args.debug:
        level=logging.DEBUG
    logging.basicConfig(level=level)

    try:
        import setproctitle
        setproctitle.setproctitle('kolejka-runner')
    except:
        pass
    
    limits = KolejkaLimits()
    limits.cpus = args.cpus
    limits.cpus_offset = args.cpus_offset
    limits.memory = args.memory
    limits.swap = args.swap
    limits.pids = args.pids
    limits.time = args.time

    env = dict(os.environ)
    kwargs = dict()
    uid = None
    user = None
    gid = None
    group = None
    groups = None
    if args.user:
        try:
            pw = pwd.getpwuid(int(args.user))
        except:
            pw = pwd.getpwnam(args.user)
        uid = pw.pw_uid
        user = pw.pw_name
        gid = pw.pw_gid
        group = grp.getgrgid(gid).gr_name
        groups = [ gid, ]
    if args.group:
        try:
            gr = grp.getgrgid(int(args.group))
        except:
            gr = grp.getgrnam(args.group)
        gid = gr.gr_gid
        group = gr.gr_name
        groups = [ gid, ]
    if user is not None and gid is not None:
        groups = os.getgrouplist(user, gid)
    if args.groups is not None:
        groups = set()
        if gid is not None:
            groups.add(gid)
        for g in args.groups.split(','):
            try:
                gr = grp.getgrgid(int(g))
            except:
                gr = grp.getgrnam(g)
            groups.add(gr.gr_gid)
        groups = list(groups)

    if args.clear_env:
        env = dict()
    for varval in args.env:
        var, val = varval.split('=', 1)
        env[var] = val

    def execute():
        stdin_file = None
        stdout_file = None
        stderr_file = None
        writers = []
        if args.stdin:
            stdin_file = file_reader(args.stdin)
        if args.stdout:
            stdout_file,stdout_writer = file_writer(args.stdout, append=args.stdout_append, max_bytes=args.stdout_max_bytes)
            writers.append(stdout_writer)
        if args.stderr:
            stderr_file,stderr_writer = file_writer(args.stderr, append=args.stderr_append, max_bytes=args.stderr_max_bytes)
            writers.append(stderr_writer)
        result = run(args.args,
            stdin=stdin_file,
            stdout=stdout_file,
            stderr=stderr_file,
            check=False,
            env=env,
            start_new_session=args.session,
            chroot=args.root,
            cwd=args.dir,
            nice=args.nice,
            umask=args.umask,
            user=uid,
            group=gid,
            groups=groups,
            limits=limits
        )
        if stdin_file:
            stdin_file.close()
        if stdout_file:
            stdout_file.close()
        if stderr_file:
            stderr_file.close()
        for writer in writers:
            writer.join()

        if args.stats_file:
            with open(args.stats_file, 'w') as stats_file:
                json.dump(result.stats.dump(), stats_file, sort_keys=2, indent=2)
        result.starter.client.close()
        return result.returncode
    
    call = execute
    if args.background:
        def daemonized():
            with daemon.DaemonContext(pidfile=args.pid_file):
                execute()
            return 0
        call = daemonized
    result = call()

    sys.exit(result)

if __name__ == '__main__':
    main()
