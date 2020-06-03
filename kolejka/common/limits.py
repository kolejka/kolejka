# vim:ts=4:sts=4:sw=4:expandtab

from .parse import parse_time, parse_memory, parse_int, parse_bool
from .parse import unparse_time, unparse_memory
from .parse import json_dict_load

def min_none(*args):
    args = [ a for a in args if a is not None ]
    if len(args) > 1:
        return min(*args)
    if len(args) > 0:
        return args[0]

def max_none(*args):
    args = [ a for a in args if a is not None ]
    if len(args) > 1:
        return max(*args)
    if len(args) > 0:
        return args[0]

def sum_none(*args):
    args = [ a for a in args if a is not None ]
    if len(args) > 1:
        return sum(args[1:], args[0])
    if len(args) > 0:
        return args[0]

class KolejkaLimits:
    def __init__(self, **kwargs):
        self.load(kwargs)

    def load(self, data, **kwargs):
        args = json_dict_load(data)
        args.update(kwargs)
        self.cpus = parse_int(args.get('cpus', None))
        self.cpus_offset = parse_int(args.get('cpus_offset', None))
        self.memory = parse_memory(args.get('memory', None))
        self.swap = parse_memory(args.get('swap', None))
        self.network = parse_bool(args.get('network', None))
        self.pids = parse_int(args.get('pids', None))
        self.storage = parse_memory(args.get('storage', None))
        self.image = parse_memory(args.get('image', None))
        self.workspace = parse_memory(args.get('workspace', None))
        self.time = parse_time(args.get('time', None))

    def dump(self):
        res = dict()
        if self.cpus is not None:
            res['cpus'] = self.cpus
        if self.cpus_offset is not None:
            res['cpus_offset'] = self.cpus_offset
        if self.memory is not None:
            res['memory'] = unparse_memory(self.memory)
        if self.swap is not None:
            res['swap'] = unparse_memory(self.swap)
        if self.network is not None:
            res['network'] = self.network
        if self.pids is not None:
            res['pids'] = self.pids
        if self.storage is not None:
            res['storage'] = unparse_memory(self.storage)
        if self.image is not None:
            res['image'] = unparse_memory(self.image)
        if self.workspace is not None:
            res['workspace'] = unparse_memory(self.workspace)
        if self.time is not None:
            res['time'] = unparse_time(self.time)
        return res

    def update(self, other):
        self.cpus = min_none(self.cpus, other.cpus)
        self.cpus_offset = min_none(self.cpus_offset, other.cpus_offset)
        self.memory = min_none(self.memory, other.memory)
        self.swap = min_none(self.swap, other.swap)
        self.network = min_none(self.network, other.network)
        self.pids = min_none(self.pids, other.pids)
        self.storage = min_none(self.storage, other.storage)
        self.image = min_none(self.image, other.image)
        self.workspace = min_none(self.workspace, other.workspace)
        self.time = min_none(self.time, other.time)

class KolejkaStats:
    class CpusStats:
        def __init__(self, **kwargs):
            self.load(kwargs)
        def load(self, data, **kwargs):
            args = json_dict_load(data)
            args.update(kwargs)
            self.usage = parse_time(args.get('usage', None))
            self.system = parse_time(args.get('system', None))
            self.user = parse_time(args.get('user', None))
            self.usage = max_none(self.usage, sum_none(self.system, self.user))
        def dump(self):
            res = dict()
            if self.usage is not None:
                res['usage'] = unparse_time(self.usage)
            if self.system is not None:
                res['system'] = unparse_time(self.system)
            if self.user is not None:
                res['user'] = unparse_time(self.user)
            return res
        def update(self, other):
            self.usage = max_none(self.usage, other.usage)
            self.system = max_none(self.system, other.system)
            self.user = max_none(self.user, other.user)
            self.usage = max_none(self.usage, sum_none(self.system, self.user))
        def add(self, other):
            self.usage = sum_none(self.usage, other.usage)
            self.system = sum_none(self.system, other.system)
            self.user = sum_none(self.user, other.user)
            self.usage = max_none(self.usage, sum_none(self.system, self.user))

    class MemoryStats:
        def __init__(self, **kwargs):
            self.load(kwargs)
        def load(self, data, **kwargs):
            args = json_dict_load(data)
            args.update(kwargs)
            self.usage = parse_memory(args.get('usage', None))
            self.max_usage = parse_memory(args.get('max_usage', None))
            self.max_usage = max_none(self.max_usage, self.usage)
            self.swap = parse_memory(args.get('swap', None))
            self.max_swap = parse_memory(args.get('max_swap', None))
            self.max_swap = max_none(self.max_swap, self.swap)
            self.failures = parse_int(args.get('failures', None))
        def dump(self):
            res = dict()
            if self.usage is not None:
                res['usage'] = unparse_memory(self.usage)
            if self.max_usage is not None:
                res['max_usage'] = unparse_memory(self.max_usage)
            if self.swap is not None:
                res['swap'] = unparse_memory(self.swap)
            if self.max_swap is not None:
                res['max_swap'] = unparse_memory(self.max_swap)
            if self.failures is not None:
                res['failures'] = self.failures
            return res
        def update(self, other):
            if other.usage is not None:
                self.usage = other.usage
            self.max_usage = max_none(self.max_usage, other.max_usage, self.usage)
            if other.swap is not None:
                self.swap = other.swap
            self.max_swap = max_none(self.max_swap, other.max_swap, self.swap)
            self.failures = max_none(self.failures, other.failures)

    class PidsStats:
        def __init__(self, **kwargs):
            self.load(kwargs)
        def load(self, data, **kwargs):
            args = json_dict_load(data)
            args.update(kwargs)
            self.usage = parse_int(args.get('usage', None))
            self.max_usage = parse_int(args.get('max_usage', None))
            self.max_usage = max_none(self.max_usage, self.usage)
            self.failures = parse_int(args.get('failures', None))
        def dump(self):
            res = dict()
            if self.usage is not None:
                res['usage'] = self.usage
            if self.max_usage is not None:
                res['max_usage'] = self.max_usage
            if self.failures is not None:
                res['failures'] = self.failures
            return res
        def update(self, other):
            if other.usage is not None:
                self.usage = other.usage
            self.max_usage = max_none(self.max_usage, other.max_usage, self.usage)
            self.failures = max_none(self.failures, other.failures)

    def __init__(self, **kwargs):
        self.load(kwargs)

    def load(self, data, **kwargs):
        args = json_dict_load(data)
        args.update(kwargs)
        self.cpu = KolejkaStats.CpusStats()
        self.cpu.load(args.get('cpu', {}))
        self.cpus = dict()
        for key, val in args.get('cpus', {}).items():
            self.cpus[key] = KolejkaStats.CpusStats()
            self.cpus[key].load(val)
        sumcpus = KolejkaStats.CpusStats()
        for key,val in self.cpus.items():
            sumcpus.add(val)
        self.cpu.update(sumcpus)
        self.memory = KolejkaStats.MemoryStats()
        self.memory.load(args.get('memory', {}))
        self.pids = KolejkaStats.PidsStats()
        self.pids.load(args.get('pids', {}))
        self.time = parse_time(args.get('time', None))

    def dump(self):
        res = dict()
        res['cpu'] = self.cpu.dump()
        res['cpus'] = dict( [ (k, v.dump()) for k,v in self.cpus.items() ] )
        res['memory'] = self.memory.dump()
        res['pids'] = self.pids.dump()
        if self.time is not None:
            res['time'] = unparse_time(self.time)
        return res

    def update(self, other):
        self.cpu.update(other.cpu)
        for k,v in other.cpus.items():
            if k not in self.cpus:
                self.cpus[k] = KolejkaStats.CpusStats()
            self.cpus[k].update(v)
        sumcpus = KolejkaStats.CpusStats()
        for key,val in self.cpus.items():
            sumcpus.add(val)
        self.cpu.update(sumcpus)
        self.memory.update(other.memory)
        self.pids.update(other.pids)
        self.time = max_none(self.time, other.time)
