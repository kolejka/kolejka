# vim:ts=4:sts=4:sw=4:expandtab

import cgi
import datetime
import hashlib
import http.server
import json
import logging
from multiprocessing import Process
import os
import re
import signal
import socket
import socketserver
import time
import traceback
from urllib.parse import urlparse, urlencode, parse_qsl
import uuid

from kolejka.common.settings import OBSERVER_CGROUPS, OBSERVER_PID_FILE, OBSERVER_SERVERSTRING
from kolejka.common import HTTPUnixServer, HTTPUnixConnection
from kolejka.common import KolejkaLimits, KolejkaStats
from kolejka.common import ControlGroupSystem

#TODO: detect subsessions?

class Session:
    @property
    def system(self):
        return self.registry.control_group_system

    @property
    def group_name(self):
        return 'kolejka_observer_' + self.id

    def group_path(self, group, filename=''):
        assert group in self.groups
        return os.path.join(self.system.mount_point(group), self.groups[group].strip('/'), filename.strip('/')).rstrip('/')

    def parent_group_path(self, group, filename=''):
        assert group in self.groups
        return os.path.join(self.system.mount_point(group), self.parent_groups[group].strip('/'), filename.strip('/')).rstrip('/')

    def list_group(self, group):
        result = set()
        path = self.group_path(group)
        for d, _, _ in os.walk(path):
            group_list_path = os.path.join(path, d, 'cgroup.procs')
            if os.path.exists(group_list_path):
                with open(group_list_path) as group_list_file:
                    result.update([line.strip() for line in group_list_file.readlines()])
        return sorted(list(result))

    def cpuset_cpus(self, path):
        path=os.path.abspath(path)
        while path.startswith(self.system.mount_point('cpuset')):
            cpuset_path = os.path.join(path, 'cpuset.cpus')
            if os.path.exists(cpuset_path):
                with open(cpuset_path) as cpuset_file:
                    cpus = cpuset_file.readline().strip()
                if cpus != '':
                    cpuset = self.system.parse_cpuset(cpus)
                    return sorted(list(cpuset))
            path = os.path.dirname(path)
    def limited_cpus(self):
        return self.cpuset_cpus(self.group_path('cpuset'))
    def available_cpus(self):
        return self.cpuset_cpus(os.path.dirname(self.group_path('cpuset')))

    def pid_start_time(self, pid):
        try:
            stat_path = os.path.join('/proc', str(pid), 'stat')
            with open(stat_path) as stat_file:
                stats = stat_file.read()
            stats = re.sub(r'^[^)]*\) ', '', stats).split()
            return int(stats[19])
        except:
            pass

    def limited_pids(self):
        path = self.group_path('pids')
        result = 2**16
        while path.startswith(self.system.mount_point('pids')):
            pids_path = os.path.join(path, 'pids.max')
            if os.path.exists(pids_path):
                with open(pids_path) as pids_file:
                    pids = pids_file.readline().strip()
                if pids != '' and pids != 'max':
                    result = min(result, int(pids))
            path = os.path.dirname(path)
        return result

    def finished(self):
        if self.pid_start_time(self.creator_pid) == self.creator_start_time:
            return False
        if len(self.list_group('pids')) > 0:
            return False
        return True

    def __init__(self, registry, session_id, pid):
        self.registry = registry
        self.id = session_id
        self.creator_pid = pid
        self.creator_start_time = self.pid_start_time(self.creator_pid)
        pid_groups = self.system.pid_groups(pid)
        self.parent_groups = dict()
        self.groups = dict()
        for group in OBSERVER_CGROUPS:
            self.parent_groups[group] = pid_groups[group]
            self.groups[group] = os.path.join(self.parent_groups[group], self.group_name)
        for group in OBSERVER_CGROUPS:
            if group == 'memory':
                with open(os.path.join(os.path.dirname(self.group_path(group)), 'memory.use_hierarchy')) as f:
                    use_hierarchy = bool(f.readline().strip())
                    assert use_hierarchy
            os.makedirs(self.group_path(group), exist_ok=True)
            if group == 'cpuset':
                for inherit in ['cpuset.cpus', 'cpuset.mems']:
                    with open(os.path.join(os.path.dirname(self.group_path(group)), inherit)) as f:
                        with open(os.path.join(self.group_path(group), inherit), 'w') as t:
                            t.write(f.read())
        logging.debug('Created session %s with paths [%s] for pid %s'%(self.id, ','.join(self.groups.values()), self.creator_pid))
        self.start_time = time.perf_counter()
        self.close_time = None

    def attach(self, pid):
        pid_groups = self.system.pid_groups(pid)
        for group in OBSERVER_CGROUPS:
            assert os.path.join(pid_groups[group], self.group_name) == self.groups[group]
        for group in OBSERVER_CGROUPS:
            tasks_path = self.group_path(group, filename='tasks')
            assert os.path.isfile(tasks_path)
            with open(tasks_path, 'w') as tasks_file:
                tasks_file.write(str(pid))
        logging.debug('Attached process %s to session %s'%(str(pid), self.id))

    def detach(self, pid):
        pid_groups = self.system.pid_groups(pid)
        for group in OBSERVER_CGROUPS:
            assert os.path.join(pid_groups[group], self.group_name) == self.groups[group] or pid_groups[group] == self.groups[group]
        for group in OBSERVER_CGROUPS:
            tasks_path = self.parent_group_path(group, filename='tasks')
            assert os.path.isfile(tasks_path)
            with open(tasks_path, 'w') as tasks_file:
                tasks_file.write(str(pid))
        logging.debug('Detached process %s from session %s'%(str(pid), self.id))

    def limits(self, limits=KolejkaLimits()):
        if limits.memory is not None:
            assert 'memory' in self.groups
            limit_file = self.group_path('memory', filename='memory.limit_in_bytes')
            with open(limit_file, 'w') as f:
                f.write(str(limits.memory))
            logging.debug('Limited session %s memory to %s bytes'%(self.id, limits.memory))
            if limits.swap is not None:
                assert 'memory' in self.groups
                limit_file = self.group_path('memory', filename='memory.memsw.limit_in_bytes')
                with open(limit_file, 'w') as f:
                    f.write(str(limits.memory+limits.swap))
                logging.debug('Limited session %s swap to %s bytes'%(self.id, limits.swap))
        if limits.cpus is not None:
            assert 'cpuset' in self.groups
            cpuset_cpus = self.available_cpus()
            logging.debug('Available cpus: %s', ','.join([str(c) for c in cpuset_cpus]))
            cpus_offset = limits.cpus_offset or 0
            if len(cpuset_cpus) < cpus_offset + limits.cpus:
                cpus_offset = 0
            if len(cpuset_cpus) > cpus_offset + limits.cpus:
                cpuset_cpus = cpuset_cpus[0:limits.cpus]
            limit_file = self.group_path('cpuset', filename='cpuset.cpus')
            with open(limit_file, 'w') as f:
                f.write(','.join([str(c) for c in cpuset_cpus]))
            logging.debug('Limited session %s cpus to %s'%(self.id, ','.join([str(c) for c in cpuset_cpus])))
        if limits.pids is not None:
            assert 'pids' in self.groups
            limit_file = self.group_path('pids', filename='pids.max')
            with open(limit_file, 'w') as f:
                f.write(str(limits.pids))
            logging.debug('Limited session %s pids to %s'%(self.id, limits.pids))
        if limits.time is not None:
            self.close_time = self.start_time + limits.time.total_seconds()
            logging.debug('Limited session %s time to %f'%(self.id, limits.time.total_seconds()))
        else:
            self.close_time = None

    def freeze(self, freeze=True):
        assert 'freezer' in self.groups
        if freeze:
            command = 'FROZEN'
        else:
            command = 'THAWED'
        state_file = self.group_path('freezer', filename='freezer.state')
        with open(state_file, 'w') as f:
            f.write(command)
        logging.debug('%s session %s'%(command, self.id))
        if freeze:
            while True:
                with open(state_file) as f:
                    if f.readline().strip().lower() == 'frozen':
                        return
        #TODO: wait for FROZEN. Is this code good?

    def freezing(self):
        assert 'freezer' in self.groups
        state_file = self.group_path('freezer', filename='freezer.self_freezing')
        with open(state_file) as f:
            return f.readline().strip() == '1'

    def stats(self):
        stats = self.system.groups_stats(self.groups)
        time_stats = KolejkaStats()
        time_stats.time = datetime.timedelta(seconds = max(0, time.perf_counter() - self.start_time))
        stats.update(time_stats)
        return stats

    def kill(self):
        state = self.freezing()
        self.freeze(freeze=True)

        pids = self.list_group('pids')
        for pid in pids:
            try:
                os.kill(int(pid), signal.SIGKILL)
            except OSError:
                pass
        logging.debug('KILLED session %s'%(self.id))

        self.freeze(freeze=state)

    def close(self):
        try:
            self.kill()
        except:
            pass
        try:
            self.freeze(freeze=False)
        except:
            pass
        time.sleep(0.1) #TODO: Allow thawed killed processes to die. HOW?
        self.system.groups_close(self.groups)
        logging.debug('CLOSED session %s'%(self.id))
            
class SessionRegistry:
    def __init__(self):
        self.sessions = dict()
        self.session_stats = dict()
        self.control_group_system = ControlGroupSystem()
        self.salt = uuid.uuid4().hex 

    def cleanup(self):
        for session_id in dict(self.sessions):
            self.close(session_id)

    def cleanup_finished(self):
        current_time = time.perf_counter()
        for session_id, session in list(self.sessions.items()):
            if session.close_time is not None and session.close_time < current_time:
                self.close(session_id)
            if session.finished():
                self.close(session_id)
        for session_id, stats in list(self.session_stats.items()):
            if session_id in self.sessions:
                continue
            stats_time = stats[1]
            if stats_time + 300 < current_time:
                del self.session_stats[session_id]

    def open(self, session_id, pid):
        if session_id not in self.sessions:
            self.sessions[session_id] = Session(self, session_id, pid)

    def attach(self, session_id, pid):
        if session_id not in self.sessions:
            self.sessions[session_id] = Session(self, session_id, pid)
        return self.sessions[session_id].attach(pid=pid);

    def detach(self, session_id, pid):
        assert session_id in self.sessions
        return self.sessions[session_id].detach(pid=pid);

    def limits(self, session_id, limits=KolejkaLimits()):
        assert session_id in self.sessions
        return self.sessions[session_id].limits(limits=limits)

    def stats(self, session_id):
        if session_id in self.sessions:
            current_time = time.perf_counter()
            stats = self.session_stats.get(session_id, (KolejkaStats(), 0))[0]
            stats.update(self.sessions[session_id].stats())
            self.session_stats[session_id] = (stats, current_time)
        return self.session_stats.get(session_id, (KolejkaStats(), 0))[0]

    def freeze(self, session_id):
        assert session_id in self.sessions
        return self.sessions[session_id].freeze(freeze=True)

    def thaw(self, session_id):
        assert session_id in self.sessions
        return self.sessions[session_id].freeze(freeze=False)

    def kill(self, session_id):
        if session_id not in self.sessions:
            return
        self.sessions[session_id].kill()

    def close(self, session_id):
        if session_id not in self.sessions:
            return
        try:
            try:
                self.stats(session_id)
            except:
                pass
            self.sessions[session_id].close()
            del self.sessions[session_id]
        except:
            pass

class ObserverServer(socketserver.ThreadingMixIn, HTTPUnixServer):
    def __enter__(self, *args, **kwargs):
        super().__enter__(*args, **kwargs)
        self.session_registry = SessionRegistry()
        return self
    def __exit__(self, *args, **kwargs):
        self.session_registry.cleanup()
        super().__exit__(*args, **kwargs)

class ObserverHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.mute_log_request = False
        super().__init__(*args, **kwargs)
    @property
    def session_registry(self):
        return self.server.session_registry
    def version_string(self):
        return OBSERVER_SERVERSTRING

    def send_json(self, result=None, code=200, message=None):
        try:
            result = json.dumps(result)
        except:
            logging.warning(traceback.format_exc())
            self.send_error(500)
            self.end_headers()
            return
        else:
            result = bytes(result, 'utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', len(result))
            self.end_headers()
            self.wfile.write(result)

    def log_request(self, *args, **kwargs):
        if not self.mute_log_request:
            super().log_request(*args, **kwargs)

    def do_HEAD(self):
        self.mute_log_request = True
        self.session_registry.cleanup_finished()
        self.send_response(200)
        self.end_headers()
        self.mute_log_request = False

    def do_GET(self, params_override={}):
        self.session_registry.cleanup_finished()
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        self.session_registry.cleanup_finished()
        try:
            post_data = dict()
            if 'Content-Length' in self.headers:
                post_length   = int(self.headers['Content-Length'])
                if 'Content-Type' in self.headers:
                    post_type, post_type_dict  = cgi.parse_header(self.headers['Content-Type'])
                    assert post_type == 'application/json'
                    post_charset = post_type_dict.get('charset', 'utf-8')
                    post_data = json.loads(self.rfile.read(post_length).decode(post_charset))
            url = urlparse(self.path)
            path = url.path.strip('/ ').lower()
            assert re.match(r'[a-z]*', path)
        except:
            logging.warning(traceback.format_exc())
            self.send_error(400)
            self.end_headers()
            return
        else:
            return self.cmd(path, post_data)

    def cmd(self, path, params):
        check_session = False
        fun = self.cmd_default
        if path == '':
            fun = self.cmd_root
        elif path == 'open':
            fun = self.cmd_open
        elif path == 'attach':
            fun = self.cmd_attach
            if 'session_id' in params:
                check_session = True
        elif path == 'detach':
            fun = self.cmd_detach
            check_session = True
        elif path == 'limits':
            fun = self.cmd_limits
            check_session = True
        elif path == 'stats':
            if 'session_id' not in params:
                self.send_error(400)
                self.end_headers()
                return
            fun = self.cmd_stats
        elif path == 'freeze':
            fun = self.cmd_freeze
            check_session = True
        elif path == 'thaw':
            fun = self.cmd_thaw
            check_session = True
        elif path == 'kill':
            fun = self.cmd_kill
            check_session = True
        elif path == 'close':
            fun = self.cmd_close
            check_session = True

        if 'group' in params:
            group = params['group']
            if not re.match(r'[a-z0-9_.]*', group) or len(group) > 32:
                self.send_error(403)
                self.end_headers()
                return

        if check_session:
            if not self.check_secret(params.get('session_id', ''), params.get('secret', '')):
                self.send_error(403)
                self.end_headers()
                return
        try:
            result = fun(params)
        except:
            logging.warning(traceback.format_exc())
            self.send_error(500)
            self.end_headers()
            return
        else:
            self.send_json(result)

    def cmd_default(self, params):
        raise Exception('method unknown')

    def cmd_root(self, params):
        result = dict()
        result['sessions'] = len(self.session_registry.sessions)
        result['status'] = 'ok'
        return result

    class std_params:
        def __init__(self, params):
            self.session_id = params.get('session_id', None)
            self.secret = params.get('secret', None)
            self.limits = KolejkaLimits()
            self.limits.load(params.get('limits', {}))

    def cmd_open(self, params):
        result = dict()
        params['session_id'] = self.generate_session_id()
        params['secret'] = self.generate_secret(params['session_id'])
        pid = int(self.client_address[0])
        sparams = ObserverHandler.std_params(params)
        self.session_registry.open(sparams.session_id, pid)
        result['session_id'] = sparams.session_id
        result['secret'] = sparams.secret
        result['status'] = 'ok'
        return result

    def cmd_attach(self, params):
        result = dict()
        if 'session_id' not in params:
            params['session_id'] = self.generate_session_id()
            params['secret'] = self.generate_secret(params['session_id'])
            result['session_id'] = params['session_id']
            result['secret'] = params['secret']
        pid = int(self.client_address[0])
        sparams = ObserverHandler.std_params(params)
        self.session_registry.attach(sparams.session_id, pid)
        result['status'] = 'ok'
        return result

    def cmd_detach(self, params):
        result = dict()
        pid = int(self.client_address[0])
        sparams = ObserverHandler.std_params(params)
        self.session_registry.detach(sparams.session_id, pid)
        result['status'] = 'ok'
        return result

    def cmd_limits(self, params):
        result = dict()
        sparams = ObserverHandler.std_params(params)
        self.session_registry.limits(sparams.session_id, limits = sparams.limits)
        result['status'] = 'ok'
        return result

    def cmd_stats(self, params):
        sparams = ObserverHandler.std_params(params)
        result = self.session_registry.stats(sparams.session_id).dump()
        result['status'] = 'ok'
        return result

    def cmd_freeze(self, params):
        result = dict() 
        sparams = ObserverHandler.std_params(params)
        self.session_registry.freeze(sparams.session_id)
        result['status'] = 'ok'
        return result

    def cmd_thaw(self, params):
        result = dict() 
        sparams = ObserverHandler.std_params(params)
        self.session_registry.thaw(sparams.session_id)
        result['status'] = 'ok'
        return result

    def cmd_kill(self, params):
        result = dict() 
        sparams = ObserverHandler.std_params(params)
        self.session_registry.kill(sparams.session_id)
        result['status'] = 'ok'
        return result

    def cmd_close(self, params):
        result = dict() 
        sparams = ObserverHandler.std_params(params)
        self.session_registry.close(sparams.session_id)
        result['status'] = 'ok'
        return result

    def generate_session_id(self):
        return uuid.uuid4().hex

    def generate_secret(self, session_id):
        return hashlib.sha1(bytes(self.session_registry.salt+session_id, 'utf-8')).hexdigest()

    def check_secret(self, session_id, secret):
        return secret and session_id and secret == self.generate_secret(session_id)

class KolejkaObserverServer(ObserverServer):
    def __init__(self, socket_path):
        self.socket_path = os.path.realpath(os.path.abspath(socket_path))
        socket_dir_path = os.path.dirname(self.socket_path)
        os.makedirs(socket_dir_path, exist_ok=True)
        assert os.path.isdir(socket_dir_path)
        super().__init__(self.socket_path, ObserverHandler)

    def __enter__(self, *args, **kwargs):
        super().__enter__(*args, **kwargs)
        def scheduler_func(parent, socket_path):
            while os.getppid() == parent:
                time.sleep(1)
                try:
                    connection = HTTPUnixConnection(socket_path)
                    connection.request('HEAD', '/')
                    with connection.getresponse() as response:
                        response.read()
                    connection.close()
                except:
                    traceback.print_exc()
                    pass
        self.scheduler = Process(target=scheduler_func, args=(os.getpid(), self.socket_path))
        self.scheduler.start()
        return self
    def __exit__(self, *args, **kwargs):
        self.scheduler.terminate()
        self.scheduler.join()
        return super().__exit__(*args, **kwargs)

def config_parser(parser):
    from kolejka.common.settings import OBSERVER_SOCKET
    from kolejka.observer import KolejkaObserverServer
    parser.add_argument("-s", "--socket", type=str, default=OBSERVER_SOCKET, help='listen on socket')
    parser.add_argument("--detach", action="store_true", default=False, help='run in background')
    parser.add_argument("--pid-file", type=str, default=OBSERVER_PID_FILE, help='pid file')
    def execute(args):
        with KolejkaObserverServer(args.socket) as server:
            def action():
                return server.serve_forever()
            if args.detach:
                with daemon.DaemonContext(pidfile=args.pid_file):
                    action()
            else:
                action()
    parser.set_defaults(execute=execute)

def main():
    import argparse
    import daemon
    import logging
    import os
    import setproctitle
    import traceback

    setproctitle.setproctitle('kolejka-observer')
    parser = argparse.ArgumentParser(description='KOLEJKA observer')
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help='show more info')
    parser.add_argument("-d", "--debug", action="store_true", default=False, help='show debug info')
    config_parser(parser)
    args = parser.parse_args()
    level=logging.WARNING
    if args.verbose:
        level=logging.INFO
    if args.debug:
        level=logging.DEBUG
    logging.basicConfig(level=level)
    args.execute(args)

if __name__ == '__main__':
    main()
