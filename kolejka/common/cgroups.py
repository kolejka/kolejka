# vim:ts=4:sts=4:sw=4:expandtab

import glob
import logging
import os
import re
import traceback

from .limits import KolejkaStats

class ControlGroupSystem:
    def __init__(self):
        assert os.path.exists('/proc/cgroups')
        available_groups = set()
        with open('/proc/cgroups') as cgroups_file:
            for line in cgroups_file.readlines():
                if not line.startswith('#'):
                    cgroup, hierarchy, num_cgroups, enabled = re.split(r'\s+', line.strip())
                    available_groups.add(cgroup)

        self.mount_points = dict()
        with open('/proc/mounts') as mounts_file:
            for line in mounts_file.readlines():
                dev, path, fs, opts, _, _ = re.split(r'\s+', line.strip()) 
                if fs == 'cgroup':
                    groups = opts.split(',')
                    named=False
                    for group in groups:
                        if re.match(r'^name=.*', group):
                            group = group[len('name='):]
                            logging.debug('Found \'{}\' control group at mount point \'{}\''.format(group, path))
                            self.mount_points[group] = path
                            named=True
                    if not named:
                        for group in available_groups:
                            if group in groups:
                                logging.debug('Found \'{}\' control group at mount point \'{}\''.format(group, path))
                                self.mount_points[group] = path

    def mount_point(self, group):
        assert group in self.mount_points
        return self.mount_points[group]

    def full_groups(self):
        return dict([(k, '/') for k in self.mount_points])

    def pid_groups(self, pid):
        cgroups_path = os.path.join('/proc', str(pid), 'cgroup')
        result = dict()
        with open(cgroups_path) as cgroups_file:
            for line in cgroups_file.readlines():
                num, groups, path, = re.split(r':', line.strip())
                for group in re.split(r',', groups):
                    result[group] = path
        #logging.debug('Control groups for pid {} : {}'.format(pid, ', '.join([k+':'+v for k,v in result.items()])))
        return result

    def name_groups(self, name):
        result = dict()
        for group, mp in self.mount_points.items():
            search = glob.glob(os.path.join(mp,'**',name), recursive=True)
            if len(search) == 1:
                if os.path.isdir(search[0]):
                    result[group] = search[0][len(mp)+1:]
        #logging.debug('Control groups for name {} : {}'.format(name, ', '.join([k+':'+v for k,v in result.items()])))
        return result

    def parse_cpuset(self, cpus):
        cpuset=set()
        for cpu_range in cpus.split(','):
            cpu_range = cpu_range.split('-')
            if len(cpu_range) == 1:
                cpuset.add(int(cpu_range[0]))
            else:
                for cpu in range(int(cpu_range[0]), int(cpu_range[1])+1):
                    cpuset.add(cpu)
        return cpuset

    def groups_cpuset(self, groups):
        with open(os.path.join(self.mount_point('cpuset'), groups['cpuset'].strip('/'), 'cpuset.cpus')) as cpuset_file:
            return self.parse_cpuset(cpuset_file.readline().strip())

    def full_cpuset(self):
        return self.groups_cpuset(self.full_groups())

    def pid_cpuset(self, pid=None):
        if pid is None:
            pid = os.getid()
        return self.groups_cpuset(self.pid_groups(pid))

    def name_cpuset(self, name):
        return self.groups_cpuset(self.name_groups(name))

    def limited_cpuset(self, cpuset, cpus, cpus_offset=None):
        if cpus_offset is None:
            cpus_offset = 0
        cpuset = sorted(list(cpuset))
        cpus = min(cpus, len(cpuset))
        cpus_offset %= len(cpuset)
        return set((2*cpuset)[cpus_offset:cpus_offset+cpus])

    def groups_stats(self, groups):
        result = KolejkaStats()
        if 'cpuacct' in groups and 'cpuacct' in self.mount_points:
            user_hz = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
            total = 0
            stats = { 'user' : 0, 'system' : 0 }
            try:
                usage_file = os.path.join(self.mount_point('cpuacct'), groups['cpuacct'].strip('/'), 'cpuacct.usage')
                with open(usage_file) as f:
                    total = 10**-9*float(f.readline().strip())
            except:
                pass
            try:
                usage_file = os.path.join(self.mount_point('cpuacct'), groups['cpuacct'].strip('/'), 'cpuacct.stat')
                with open(usage_file) as f:
                    stats = dict([line.strip().split() for line in f.readlines()])
            except:
                pass
            result.cpu = KolejkaStats.CpusStats(usage = total, user = float(stats['user'])/user_hz, system = float(stats['system'])/user_hz)
            usage_file = os.path.join(self.mount_point('cpuacct'), groups['cpuacct'].strip('/'), 'cpuacct.usage_percpu')
            try:
                with open(usage_file) as f:
                    cpusplit = f.readline().strip().split()
                for i,c in zip(range(len(cpusplit)), cpusplit):
                    result.cpus[str(i)] = KolejkaStats.CpusStats(usage = 10**-9*float(c))
            except:
                pass
        if 'memory' in groups and 'memory' in self.mount_points:
            try:
                usage_file = os.path.join(self.mount_point('memory'), groups['memory'].strip('/'), 'memory.usage_in_bytes')
                with open(usage_file) as f:
                    result.memory.usage = int(f.readline().strip())
            except:
                pass
            try:
                usage_file = os.path.join(self.mount_point('memory'), groups['memory'].strip('/'), 'memory.max_usage_in_bytes')
                with open(usage_file) as f:
                    result.memory.max_usage = max(result.memory.usage, int(f.readline().strip()))
            except:
                pass
            try:
                usage_file = os.path.join(self.mount_point('memory'), groups['memory'].strip('/'), 'memory.memsw.usage_in_bytes')
                with open(usage_file) as f:
                    result.memory.swap = max(0, int(f.readline().strip()) - result.memory.usage)
            except:
                pass
            try:
                usage_file = os.path.join(self.mount_point('memory'), groups['memory'].strip('/'), 'memory.memsw.max_usage_in_bytes')
                with open(usage_file) as f:
                    result.memory.max_swap = max(result.memory.swap, int(f.readline().strip()) - result.memory.max_usage)
            except:
                pass
            try:
                usage_file = os.path.join(self.mount_point('memory'), groups['memory'].strip('/'), 'memory.failcnt')
                with open(usage_file) as f:
                    result.memory.failures = int(f.readline().strip())
            except:
                pass
        if 'pids' in groups and 'pids' in self.mount_points:
            usage_file = os.path.join(self.mount_point('pids'), groups['pids'].strip('/'), 'pids.current')
            with open(usage_file) as f:
                result.pids.usage = int(f.readline().strip())
            try:
                usage_file = os.path.join(self.mount_point('pids'), groups['pids'].strip('/'), 'pids.events')
                with open(usage_file) as f:
                    stats = dict([line.strip().split() for line in f.readlines()])
                    result.pids.failures = int(stats['max'])
            except:
                pass
        result.update(KolejkaStats())
        return result

    def pid_stats(self, pid=None):
        if pid is None:
            pid = os.getid()
        return self.groups_stats(self.pid_groups(pid))

    def name_stats(self, name):
        return self.groups_stats(self.name_groups(name))

    def groups_close(self, groups):
        for group in sorted(groups, key=lambda x: 1 if x == 'freezer' else 0):
            if group in self.mount_points:
                try:
                    src_path = os.path.join(self.mount_point(group), groups[group].strip('/'))
                    dst_path = os.path.normpath(os.path.join(os.path.dirname(src_path), 'tasks'))
                    for d, _, _ in os.walk(src_path, topdown=False):
                        group_list_file = os.path.join(src_path, d, 'cgroup.procs')
                        if os.path.exists(group_list_file):
                            try:
                                with open(dst_path, 'w') as dst_file:
                                    with open(group_list_file) as src_file:
                                        dst_file.write(src_file.read())
                            except:
                                pass
                        os.rmdir(os.path.join(src_path, d))
                except:
                    traceback.print_exc()
                    pass

    def pid_close(self, pid):
        if pid is None:
            pid = os.getid()
        self.groups_close(self.pid_groups(pid))

    def name_close(self, name):
        self.groups_close(self.name_groups(name))
