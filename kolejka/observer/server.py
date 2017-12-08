# vim:ts=4:sts=4:sw=4:expandtab

import cgi
import hashlib
import http.server
import json
import logging
import os
import re
import signal
import socket
import socketserver
import traceback
from urllib.parse import urlparse, urlencode, parse_qsl
import uuid

from kolejka.common import settings
from kolejka.common import HTTPUnixServer
from kolejka.common import parse_memory, parse_time

class ControlGroupSystem:
    def __init__(self):
        assert os.path.exists('/proc/cgroups')
        available_groups = set()
        with open('/proc/cgroups') as cgroups_file:
            for line in cgroups_file.readlines():
                if not line.startswith('#'):
                    cgroup, hierarchy, num_cgroups, enabled = re.split(r'\s+', line.strip())
                    available_groups.add(cgroup)

        for group in settings.OBSERVER_CGROUPS:
            assert group in available_groups

        self.mount_points = dict()
        with open('/proc/mounts') as mounts_file:
            for line in mounts_file.readlines():
                dev, path, fs, opts, _, _ = re.split(r'\s+', line.strip()) 
                if fs == 'cgroup':
                    groups = opts.split(',')
                    for group in available_groups:
                        if group in groups:
                            logging.debug('Found \'%s\' control group at mount point \'%s\''%(group, path))
                            self.mount_points[group] = path

        for group in settings.OBSERVER_CGROUPS:
            assert group in self.mount_points

    def mount_point(self, group):
        assert group in self.mount_points
        return self.mount_points[group]

    def process_groups(self, pid):
        cgroups_path = os.path.join('/proc', str(pid), 'cgroup')
        result = dict()
        with open(cgroups_path) as cgroups_file:
            for line in cgroups_file.readlines():
                num, groups, path, = re.split(r':', line.strip())
                for group in re.split(r',', groups):
                    result[group] = path
        return result

class Session:
    @property
    def system(self):
        return self.registry.control_group_system

    def session_group_path(self, group, path='/', subpath='/'):
        return os.path.abspath(os.path.join(self.system.mount_point(group), path.strip('/'), 'kolejka_observer_' + self.id, subpath.strip('/')))

    def group_path(self, group, subpath='/', filename=''):
        assert group in self.groups
        return os.path.join(self.groups[group], subpath.strip('/'), filename.strip('/'))

    def list_group(self, group, subpath='/'):
        result = set()
        path = self.group_path(group, subpath=subpath)
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
                    cpuset=set()
                    for cpu_range in cpus.split(','):
                        cpu_range = cpu_range.split('-')
                        if len(cpu_range) == 1:
                            cpuset.add(cpu_range[0])
                        else:
                            for cpu in range(int(cpu_range[0]), int(cpu_range[1])+1):
                                cpuset.add(cpu)
                    return sorted(list(cpuset))
            path = os.path.dirname(path)
    def limited_cpus(self, subpath='/'):
        return self.cpuset_cpus(self.group_path('cpuset', subpath=subpath))
    def available_cpus(self, subpath='/'):
        return self.cpuset_cpus(os.path.dirname(self.group_path('cpuset', subpath=subpath)))

    def limited_pids(self, subpath='/'):
        path = self.group_path('pids', subpath=subpath)
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

    def __init__(self, registry, session_id, pid):
        self.registry = registry
        self.id = session_id
        process_groups = self.system.process_groups(pid)
        self.groups = dict()
        for group in settings.OBSERVER_CGROUPS:
            self.groups[group] = self.session_group_path(group, path=process_groups[group])
        for group in settings.OBSERVER_CGROUPS:
            if group == 'memory':
                with open(os.path.join(os.path.dirname(self.groups[group]), 'memory.use_hierarchy')) as f:
                    use_hierarchy = bool(f.readline().strip())
                    assert use_hierarchy
            os.makedirs(self.groups[group], exist_ok=True)
            if group == 'cpuset':
                for inherit in ['cpuset.cpus', 'cpuset.mems']:
                    with open(os.path.join(os.path.dirname(self.groups[group]), inherit)) as f:
                        with open(os.path.join(self.groups[group], inherit), 'w') as t:
                            t.write(f.read())
        logging.debug('Created session %s with paths [%s]'%(self.id, ','.join(self.groups.values())))

    def ensure_subpath(self, group, subpath='/'):
        root_path = self.groups[group]
        result_path = os.path.normpath(os.path.join(root_path, subpath.strip('/')))
        assert result_path.startswith(root_path)
        subpath = result_path[len(root_path):].strip('/')
        if len(subpath) > 0:
            parent_path = root_path
            for part in subpath.split('/'):
                part_path = os.path.join(parent_path, part)
                if not os.path.exists(part_path):
                    if group == 'memory':
                        with open(os.path.join(parent_path, 'memory.use_hierarchy'), 'w') as f:
                            f.write('1')
                    os.makedirs(part_path, exist_ok=True)
                    if group == 'cpuset':
                        for inherit in ['cpuset.cpus', 'cpuset.mems']:
                            with open(os.path.join(os.path.dirname(self.groups[group]), inherit)) as f:
                                with open(os.path.join(self.groups[group], inherit), 'w') as t:
                                    t.write(f.read())
                parent_path = part_path

    def attach(self, subpath, pid):
        process_groups = self.system.process_groups(pid)
        for group in settings.OBSERVER_CGROUPS:
            assert self.session_group_path(group, process_groups[group]).startswith(self.groups[group])
        for group in settings.OBSERVER_CGROUPS:
            self.ensure_subpath(group, subpath)
            tasks_path = self.group_path(group, subpath=subpath, filename='tasks')
            assert os.path.isfile(tasks_path)
            with open(tasks_path, 'w') as tasks_file:
                tasks_file.write(str(pid))
        logging.debug('Attached process %s to session %s [%s]'%(str(pid), self.id, subpath))

    def limit(self, subpath, pids=None, memory=None, cpus=None, cpu_offset=0):
        if memory:
            assert 'memory' in self.groups
            limit_file = self.group_path('memory', subpath=subpath, filename='memory.limit_in_bytes')
            with open(limit_file, 'w') as f:
                f.write(str(memory))
            logging.debug('Limited session %s [%s] memory to %s bytes'%(self.id, subpath, memory))
        if cpus:
            assert 'cpuset' in self.groups
            cpuset_cpus = self.available_cpus(subpath=subpath)
            logging.debug('Available cpus: %s', ','.join([str(c) for c in cpuset_cpus]))
            if len(cpuset_cpus) < cpu_offset + cpus:
                cpu_offset = 0
            if len(cpuset_cpus) > cpu_offset + cpus:
                cpuset_cpus = cpuset_cpus[0:cpus]
            limit_file = self.group_path('cpuset', subpath=subpath, filename='cpuset.cpus')
            with open(limit_file, 'w') as f:
                f.write(','.join([str(c) for c in cpuset_cpus]))
            logging.debug('Limited session %s [%s] cpus to %s'%(self.id, subpath, ','.join([str(c) for c in cpuset_cpus])))
        if pids:
            assert 'pids' in self.groups
            limit_file = self.group_path('pids', subpath=subpath, filename='pids.max')
            with open(limit_file, 'w') as f:
                f.write(str(pids))
            logging.debug('Limited session %s [%s] pids to %s'%(self.id, subpath, pids))

    def freeze(self, subpath, freeze=True):
        assert 'freezer' in self.groups
        if freeze:
            command = 'FROZEN'
        else:
            command = 'THAWED'
        state_file = self.group_path('freezer', subpath=subpath, filename='freezer.state')
        with open(state_file, 'w') as f:
            f.write(command)
        logging.debug('%s session %s [%s]'%(command, self.id, subpath))
        if freeze:
            while True:
                with open(state_file) as f:
                    if f.readline().strip().lower() == 'frozen':
                        return
        #TODO: wait for FROZEN. Is this code good?

    def freezing(self, subpath):
        assert 'freezer' in self.groups
        state_file = self.group_path('freezer', subpath=subpath, filename='freezer.self_freezing')
        with open(state_file) as f:
            return f.readline().strip() == '1'

    def stats(self, subpath):
        result = dict()
        if 'memory' in self.groups:
            result['memory'] = dict()
            usage_file = self.group_path('memory', subpath=subpath, filename='memory.usage_in_bytes')
            with open(usage_file) as f:
                result['memory']['usage'] = int(f.readline().strip())
            usage_file = self.group_path('memory', subpath=subpath, filename='memory.max_usage_in_bytes')
            with open(usage_file) as f:
                result['memory']['max_usage'] = int(f.readline().strip())
            usage_file = self.group_path('memory', subpath=subpath, filename='memory.failcnt')
            with open(usage_file) as f:
                result['memory']['failures'] = int(f.readline().strip())
            usage_file = self.group_path('memory', subpath=subpath, filename='memory.stat')
            with open(usage_file) as f:
                stats = dict([line.strip().split() for line in f.readlines()])
                result['memory']['limit'] = int(stats['hierarchical_memory_limit'])
        if 'cpuacct' in self.groups:
            user_hz = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
            result['cpus'] = dict()
            usage_file = self.group_path('cpuacct', subpath=subpath, filename='cpuacct.usage')
            with open(usage_file) as f:
                result['cpus']['usage'] = 10**-9*float(f.readline().strip())
            usage_file = self.group_path('cpuacct', subpath=subpath, filename='cpuacct.stat')
            with open(usage_file) as f:
                stats = dict([line.strip().split() for line in f.readlines()])
            result['cpus']['user'] = float(stats['user'])/user_hz
            result['cpus']['system'] = float(stats['system'])/user_hz
            usage_file = self.group_path('cpuacct', subpath=subpath, filename='cpuacct.usage_percpu')
            with open(usage_file) as f:
                cpusplit = f.readline().strip().split()
            for i,c in zip(range(len(cpusplit)), cpusplit):
                result['cpus'][str(i)] = 10**-9*float(c)
            result['cpus']['limit'] = len(self.limited_cpus(subpath=subpath))
        if 'pids' in self.groups:
            result['pids'] = dict()
            usage_file = self.group_path('pids', subpath=subpath, filename='pids.current')
            with open(usage_file) as f:
                result['pids']['usage'] = int(f.readline().strip())
            usage_file = self.group_path('pids', subpath=subpath, filename='pids.events')
            with open(usage_file) as f:
                stats = dict([line.strip().split() for line in f.readlines()])
                result['pids']['failures'] = int(stats['max'])
            result['pids']['limit'] = self.limited_pids(subpath=subpath)
        return result

    def kill(self, subpath):
        state = self.freezing(subpath=subpath)
        self.freeze(subpath=subpath, freeze=True)

        pids = self.list_group('cpuacct', subpath=subpath)
        for pid in pids:
            try:
                os.kill(int(pid), signal.SIGKILL)
            except OSError:
                pass
        logging.debug('KILLED session %s [%s]'%(self.id, subpath))

        self.freeze(subpath=subpath, freeze=state)

    def close(self, subpath):
        state = self.freezing(subpath=subpath)
        self.freeze(subpath=subpath, freeze=True)

        for group in sorted(settings.OBSERVER_CGROUPS, key=lambda x: 1 if x == 'freezer' else 0):
            src_path = self.group_path(group, subpath=subpath)
            dst_path = os.path.normpath(os.path.join(src_path, '..', 'tasks'))
            for d, _, _ in os.walk(src_path, topdown=False):
                group_list_file = os.path.join(src_path, d, 'cgroup.procs')
                if os.path.exists(group_list_file):
                    with open(dst_path, 'w') as t:
                        with open(group_list_file) as f:
                            t.write(f.read())
                os.rmdir(os.path.join(src_path, d))
        logging.debug('CLOSED session %s [%s]'%(self.id, subpath))
            
class SessionRegistry:
    def __init__(self):
        self.sessions = dict()
        self.control_group_system = ControlGroupSystem()
        self.salt = uuid.uuid4().hex 

    def cleanup(self):
        for session_id in dict(self.sessions):
            self.close(session_id)

    def create(self, session_id, pid):
        if session_id not in self.sessions:
            self.sessions[session_id] = Session(self, session_id, pid)

    def attach(self, session_id, subpath, pid):
        if session_id not in self.sessions:
            self.sessions[session_id] = Session(self, session_id, pid)
        return self.sessions[session_id].attach(subpath=subpath, pid=pid);

    def limit(self, session_id, subpath='/', pids=None, memory=None, cpus=None, cpu_offset=0):
        assert session_id in self.sessions
        return self.sessions[session_id].limit(subpath=subpath, pids=pids, memory=memory, cpus=cpus, cpu_offset=cpu_offset)

    def stats(self, session_id, subpath='/'):
        if session_id in self.sessions:
            return self.sessions[session_id].stats(subpath=subpath)
        else:
            result = dict()
            result['memory'] = dict()
            result['memory']['max_usage'] = 0
            result['memory']['failures'] = 0
            result['memory']['limit'] = -1
            result['cpus'] = dict()
            result['cpus']['usage'] = 0
            result['cpus']['user'] = 0
            result['cpus']['system'] = 0
            result['cpus']['limit'] = -1
            result['pids'] = dict()
            result['pids']['usage'] = 0
            result['pids']['failures'] = 0
            result['pids']['limit'] = -1
            return result

    def freeze(self, session_id, subpath='/'):
        assert session_id in self.sessions
        return self.sessions[session_id].freeze(subpath=subpath, freeze=True)

    def thaw(self, session_id, subpath='/'):
        assert session_id in self.sessions
        return self.sessions[session_id].freeze(subpath=subpath, freeze=False)

    def kill(self, session_id, subpath='/'):
        if session_id not in self.sessions:
            return
        self.sessions[session_id].kill(subpath=subpath)

    def close(self, session_id, subpath='/'):
        if session_id not in self.sessions:
            return
        self.sessions[session_id].close(subpath=subpath)
        del self.sessions[session_id]

class ObserverServer(socketserver.ThreadingMixIn, HTTPUnixServer):
    def __enter__(self, *args, **kwargs):
        super().__enter__(*args, **kwargs)
        self.session_registry = SessionRegistry()
        return self
    def __exit__(self, *args, **kwargs):
        self.session_registry.cleanup()
        super().__exit__(*args, **kwargs)

class ObserverHandler(http.server.BaseHTTPRequestHandler):
    @property
    def session_registry(self):
        return self.server.session_registry
    def version_string(self):
        return settings.OBSERVER_SERVERSTRING

    def do_HEAD(self):
        self.send_response(200)

    def do_GET(self, params_override={}):
        self.send_response(200)

    def do_POST(self):
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
            assert re.match(r'[a-z]+', path)
        except:
            logging.warning(traceback.format_exc())
            self.send_error(400)
            return
        else:
            return self.cmd(path, post_data)

    def cmd(self, path, params):
        check_session = False
        fun = self.cmd_default
        if path == '':
            fun = self.cmd_root
        elif path == 'create':
            fun = self.cmd_create
        elif path == 'attach':
            fun = self.cmd_attach
            if 'session_id' in params:
                check_session = True
        elif path == 'limit':
            fun = self.cmd_limit
            check_session = True
        elif path == 'stats':
            if 'session_id' not in params:
                self.send_error(400)
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
                return

        if check_session:
            if not self.check_secret(params.get('session_id', ''), params.get('secret', '')):
                self.send_error(403)
                return
        try:
            result = fun(params)
            result = json.dumps(result)
        except:
            logging.warning(traceback.format_exc())
            self.send_error(500)
            return
        else:
            result = bytes(result, 'utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', len(result))
            self.end_headers()
            self.wfile.write(result)

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
            self.subpath = params.get('group', '/')
            self.memory = params.get('memory', None)
            if self.memory is not None:
                self.memory = parse_memory(self.memory)
            self.cpus = params.get('cpus', None)
            if self.cpus is not None:
                self.cpus = int(self.cpus)
            self.cpu_offset = int(params.get('cpu_offset', 0))
            self.pids = params.get('pids', None)
            if self.pids is not None:
                self.pids = int(self.pids)

    def cmd_create(self, params):
        result = dict()
        result['session_id'] = self.generate_session_id()
        result['secret'] = self.generate_secret(result['session_id'])
        pid = int(self.client_address[0])
        sparams = ObserverHandler.std_params(params)
        self.session_registry.create(sparams.session_id, pid)
        result['status'] = 'ok'
        return result

    def cmd_attach(self, params):
        result = dict()
        if 'session_id' not in result:
            result['session_id'] = self.generate_session_id()
            result['secret'] = self.generate_secret(result['session_id'])
        pid = int(self.client_address[0])
        sparams = ObserverHandler.std_params(params)
        self.session_registry.attach(sparams.session_id, sparams.subpath, pid)
        result['status'] = 'ok'
        return result

    def cmd_limit(self, params):
        result = dict()
        sparams = ObserverHandler.std_params(params)
        self.session_registry.limit(sparams.session_id, sparams.subpath,
                pids = sparams.pids,
                memory = sparams.memory,
                cpus = sparams.cpus,
                cpu_offset = sparams.cpu_offset)
        result['status'] = 'ok'
        return result

    def cmd_stats(self, params):
        sparams = ObserverHandler.std_params(params)
        result = self.session_registry.stats(sparams.session_id, sparams.subpath)
        result['status'] = 'ok'
        return result

    def cmd_freeze(self, params):
        result = dict() 
        sparams = ObserverHandler.std_params(params)
        self.session_registry.freeze(sparams.session_id, sparams.subpath)
        result['status'] = 'ok'
        return result

    def cmd_thaw(self, params):
        result = dict() 
        sparams = ObserverHandler.std_params(params)
        self.session_registry.thaw(sparams.session_id, sparams.subpath)
        result['status'] = 'ok'
        return result

    def cmd_kill(self, params):
        result = dict() 
        sparams = ObserverHandler.std_params(params)
        self.session_registry.kill(sparams.session_id, sparams.subpath)
        result['status'] = 'ok'
        return result

    def cmd_close(self, params):
        result = dict() 
        sparams = ObserverHandler.std_params(params)
        self.session_registry.close(sparams.session_id, sparams.subpath)
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
        socket_path = os.path.realpath(os.path.abspath(socket_path))
        socket_dir_path = os.path.dirname(socket_path)
        os.makedirs(socket_dir_path, exist_ok=True)
        assert os.path.isdir(socket_dir_path)
        super().__init__(socket_path, ObserverHandler)

def main():
    import argparse
    import logging
    import os
    import traceback
    from kolejka.common import settings
    from kolejka.observer import KolejkaObserverServer

    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--socket", type=str, default=settings.OBSERVER_SOCKET, help='listen on socket')
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help='show more info')
    parser.add_argument("-d", "--debug", action="store_true", default=False, help='show debug info')
    args = parser.parse_args()
    level=logging.WARNING
    if args.verbose:
        level=logging.INFO
    if args.debug:
        level=logging.DEBUG
    logging.basicConfig(level=level)

    try:
        with KolejkaObserverServer(args.socket) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        raise
    except:
        traceback.print_exc()
        raise
