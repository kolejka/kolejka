# vim:ts=4:sts=4:sw=4:expandtab

__import__('pkg_resources').declare_namespace('kolejka')

import json
import subprocess

from .http_socket import HTTPUnixServer, HTTPUnixConnection
from .limits import KolejkaLimits, KolejkaStats
from .task import KolejkaTask, KolejkaResult
from .parse import parse_memory, parse_time

def silent_call(*args, **kwargs):
    kwargs['stdin'] = kwargs.get('stdin', subprocess.DEVNULL)
    kwargs['stdout'] = kwargs.get('stderr', subprocess.DEVNULL)
    kwargs['stderr'] = kwargs.get('stdout', subprocess.DEVNULL)
    return subprocess.call(*args, **kwargs)
