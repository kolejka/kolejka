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

class KolejkaLimits:
    def __init__(self, **kwargs):
        self.load(kwargs)

    def load(self, data, **kwargs):
        args = json_dict_load(data)
        args.update(kwargs)
        self.cpus = parse_int(args.get('cpus', None))
        self.cpus_offset = parse_int(args.get('cpus_offset', None))
        self.memory = parse_memory(args.get('memory', None))
        self.network = parse_bool(args.get('network', None))
        self.pids = parse_int(args.get('pids', None))
        self.storage = parse_memory(args.get('storage', None))
        self.time = parse_time(args.get('time', None))

    def dump(self):
        res = dict()
        if self.cpus is not None:
            res['cpus'] = self.cpus
        if self.cpus_offset is not None:
            res['cpus_offset'] = self.cpus_offset
        if self.memory is not None:
            res['memory'] = unparse_memory(self.memory)
        if self.network is not None:
            res['network'] = self.network
        if self.pids is not None:
            res['pids'] = self.pids
        if self.storage is not None:
            res['storage'] = unparse_memory(self.storage)
        if self.time is not None:
            res['time'] = unparse_time(self.time)
        return res

    def update(self, other):
        self.cpus = min_none(self.cpus, other.cpus)
        self.cpus_offset = min_none(self.cpus_offset, other.cpus_offset)
        self.memory = min_none(self.memory, other.memory)
        self.network = min_none(self.network, other.network)
        self.pids = min_none(self.pids, other.pids)
        self.storage = min_none(self.storage, other.storage)
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

    class MemoryStats:
        def __init__(self, **kwargs):
            self.load(kwargs)
        def load(self, data, **kwargs):
            args = json_dict_load(data)
            args.update(kwargs)
            self.usage = parse_memory(args.get('usage', None))
            self.max_usage = parse_memory(args.get('max_usage', None))
            self.max_usage = max_none(self.max_usage, self.usage)
            self.failures = parse_int(args.get('failures', None))
        def dump(self):
            res = dict()
            if self.usage is not None:
                res['usage'] = unparse_memory(self.usage)
            if self.max_usage is not None:
                res['max_usage'] = unparse_memory(self.max_usage)
            if self.failures is not None:
                res['failures'] = self.failures
            return res
        def update(self, other):
            if other.usage is not None:
                self.usage = other.usage
            self.max_usage = max_none(self.max_usage, other.max_usage, self.usage)
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
        self.cpus = dict()
        for key, val in args.get('cpus', {}).items():
            self.cpus[key] = KolejkaStats.CpusStats()
            self.cpus[key].load(val)
        self.memory = KolejkaStats.MemoryStats()
        self.memory.load(args.get('memory', {}))
        self.pids = KolejkaStats.PidsStats()
        self.pids.load(args.get('pids', {}))
        self.time = parse_time(args.get('time', None))

    def dump(self):
        res = dict()
        res['cpus'] = dict( [ (k, v.dump()) for k,v in self.cpus.items() ] )
        res['memory'] = self.memory.dump()
        res['pids'] = self.pids.dump()
        if self.time is not None:
            res['time'] = unparse_time(self.time)
        return res

    def update(self, other):
        self.cpus.update(other.cpus)
        self.memory.update(other.memory)
        self.pids.update(other.pids)
        self.time = max_none(self.time, other.time)
