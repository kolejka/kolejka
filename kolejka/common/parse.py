# vim:ts=4:sts=4:sw=4:expandtab

import copy
import datetime
import json

def parse_float_with_modifiers(x, modifiers):
    modifier = 1
    x = str(x).strip()
    while len(x) > 0 and x[-1] in modifiers :
        modifier *= modifiers[x[-1]]
        x = x[:-1]
    return float(x) * modifier

def parse_time(x) :
    if x is not None:
        return datetime.timedelta(seconds=parse_float_with_modifiers(x, {
            'D' : 60**2*24,
            'H' : 60**2,
            'M' : 60,
            's' : 1,
            'm' : 10**-3,
            'µ' : 10**-6,
            'n' : 10**-9,
        }))

def unparse_time(x) :
    if x is not None:
        return str(x.total_seconds())+'s'

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
        return str(x)+'b'

def parse_int(x):
    if x is not None:
        return int(x)

def parse_str(x):
    if x is not None:
        return str(x)

def parse_float(x):
    if x is not None:
        return float(x)

def json_dict_load(data):
    if isinstance(data, dict):
        return copy.copy(data)
    if isinstance(data, list):
        return copy.copy(data)
    return json.load(data)

