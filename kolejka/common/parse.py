# vim:ts=4:sts=4:sw=4:expandtab

import argparse
import copy
import datetime
import json

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

def parse_time(x) :
    if x is not None:
        if isinstance(x, datetime.timedelta):
            return x
        return datetime.timedelta(seconds=parse_float_with_modifiers(x, {
            'W' : 60*60*24*7,
            'D' : 60*60*24,
            'H' : 60*60,
            'M' : 60,
            's' : 1,
            'm' : 10**-3,
            'µ' : 10**-6,
            'n' : 10**-9,
        }))

def unparse_time(x) :
    if x is not None:
        assert isinstance(x, datetime.timedelta)
        return str(x.total_seconds())+'s'

class TimeAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self.type = datetime.timedelta
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super().__init__(option_strings, dest, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, parse_time(values))

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

def unparse_memory(x):
    if x is not None:
        assert isinstance(x, int)
        return str(x)+'b'

class MemoryAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self.type = int
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super().__init__(option_strings, dest, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, parse_memory(values))

def parse_bool(x):
    if x is not None:
        if isinstance(x, bool):
            return x
        return str(x).lower().strip() not in [ 'false', 'no', '0' ]

def parse_int(x):
    if x is not None:
        return int(x)

def parse_float(x):
    if x is not None:
        return float(x)

def parse_str(x):
    if x is not None:
        return str(x)

def parse_str_list(x, separator=','):
    if x is not None:
        if isinstance(x, list):
            return [ str(xe) for xe in x ]
        return [ xe.strip() for xe in str(x).split(separator) if xe.strip() ]

def json_dict_load(data):
    res = dict()
    if data is None:
        pass
    elif isinstance(data, dict):
        res = copy.copy(data)
    elif isinstance(data, str):
        res = json.loads(data)
    elif isinstance(data, bytes):
        res = json.loads(str(data, "utf-8"))
    else:
        res = json.load(data)
    assert isinstance(res, dict)
    return res

def json_list_load(data):
    res = list()
    if data is None:
        pass
    elif isinstance(data, list):
        res = copy.copy(data)
    elif isinstance(data, str):
        res = json.loads(data)
    elif isinstance(data, bytes):
        res = json.loads(str(data, "utf-8"))
    else:
        res = json.load(data)
    assert isinstance(res, list)
    return res
