# vim:ts=4:sts=4:sw=4:expandtab

import grp
import json
import logging
import os
import pwd
import subprocess
import sys

from kolejka.common import KolejkaLimits
from kolejka.common import MemoryAction, TimeAction
from kolejka.observer.client import KolejkaObserverClient

class CompletedProcess(subprocess.CompletedProcess):
    def __init__(self, completed_process, stats, limits):
        self.args = completed_process.args
        self.returncode = completed_process.returncode
        self.stdout = completed_process.stdout
        self.stderr = completed_process.stderr
        self.stats = stats
        self.limits = limits

def run(args, limits=None, **kwargs):
    if limits is None:
        limits = KolejkaLimits()
    env = kwargs.get('env', dict())
    client = KolejkaObserverClient()
    session = client.open()
    session_id = session['session_id']
    secret = session['secret']
    env['KOLEJKA_RUNNER_SESSION'] = session_id
    env['KOLEJKA_RUNNER_SECRET'] = secret
    kwargs['env'] = env
    client = KolejkaObserverClient(session=session_id, secret=secret)
    runner_args = [ 'kolejka-runner', ]
    try:
        client.limits(limits)
        completed_process = subprocess.run(runner_args + args, **kwargs)
        stats = client.stats()
        return CompletedProcess(completed_process, stats, limits)
    finally:
        client.close()

def main():
    import argparse
    import daemon
    import logging
    import os
    import setproctitle

    parser = argparse.ArgumentParser(description='KOLEJKA runner')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='show more info')
    parser.add_argument('-d', '--debug', action='store_true', default=False, help='show debug info')
    parser.add_argument('--stdin', help='redirect stdin')
    parser.add_argument('--stdout', help='redirect stdout')
    parser.add_argument('--trunc-stdout', help='truncate stdout file')
    parser.add_argument('--stderr', help='redirect stderr')
    parser.add_argument('--trunc-stderr', help='truncate stderr file')
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
    parser.add_argument('--umask', help='change umask')
    parser.add_argument('--nice', help='change nice level')
#    parser.add_argument('--proc-sched', help='change process scheduler')
#    parser.add_argument('--io-sched', help='change IO scheduler')

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
    setproctitle.setproctitle('kolejka-runner')
    
    limits = KolejkaLimits()
    limits.cpus = args.cpus
    limits.cpus_offset = args.cpus_offset
    limits.memory = args.memory
    limits.swap = args.swap
    limits.pids = args.pids
    limits.time = args.time

    env = dict(os.environ)
    session_id = env.pop('KOLEJKA_RUNNER_SESSION', None)
    secret = env.pop('KOLEJKA_RUNNER_SECRET', None)
    if not session_id:
        secret = None
    client = KolejkaObserverClient(session=session_id, secret=secret)
    client.attach()
    client.limits(limits)
    kwargs = dict()
    uid = None
    gid = None
    if args.user:
        try:
            uid = int(args.user)
        except:
            pw = pwd.getpwnam(args.user)
            uid = pw.pw_uid
            gid = pw.pw_gid
    if args.group:
        try:
            gid = int(args.group)
        except:
            gid = grp.getgrnam(args.group).gr_gid

    def preexec():
        if args.pid_file is not None and not args.background:
            with open(args.pid_file, 'w') as pid_file:
                pid_file.writelines([str(os.getpid())])
        if args.root is not None:
            os.chroot(args.root)
        if args.dir is not None:
            os.chdir(args.dir)
        if args.nice is not None:
            os.nice(args.nice)
        if args.umask is not None:
            os.umask(args.umask)
        if gid is not None:
            os.setgid(gid)
        if uid is not None:
            os.setuid(uid)


    if args.clear_env:
        env = dict()
    for varval in args.env:
        var, val = varval.split('=', 1)
        env[var] = val
    kwargs['start_new_session'] = args.session
    
    kwargs['check'] = False
    kwargs['env'] = env
    kwargs['preexec_fn'] = preexec

    def execute():
        return subprocess.run(args.args, **kwargs).returncode
    call = execute
    if args.background:
        def daemonized():
            with daemon.DaemonContext(pidfile=args.pid_file):
                execute()
            return 0
        call = daemonized

    result = call()

    if args.stats_file:
        with open(args.stats_file, 'w') as stats_file:
            json.dump(client.stats().dump(), stats_file, sort_keys=2, indent=2)
    if not session_id:
        client.close()

    sys.exit(result)

if __name__ == '__main__':
    main()
