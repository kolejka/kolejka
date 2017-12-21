# vim:ts=4:sts=4:sw=4:expandtab

import logging
import os
import re

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
                    for group in available_groups:
                        if group in groups:
                            logging.debug('Found \'%s\' control group at mount point \'%s\''%(group, path))
                            self.mount_points[group] = path

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

    def my_cpus(self):
        pgs = self.process_groups(os.getpid())
        with open(os.path.join(self.mount_point('cpuset'), pgs['cpuset'].strip('/'), 'cpuset.cpus')) as cpuset_file:
            return self.parse_cpuset(cpuset_file.readline().strip())

    def limited_cpus(self, cpus, cpus_offset=None, cpuset=None):
        if cpus_offset is None:
            cpus_offset = 0
        if cpuset is None:
            cpuset = self.my_cpus()
        cpuset = sorted(list(cpuset))
        cpus = min(cpus, len(cpuset))
        cpus_offset %= len(cpuset)
        return set((2*cpuset)[cpus_offset:cpus_offset+cpus])
