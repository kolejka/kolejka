# vim:ts=4:sts=4:sw=4:expandtab

__import__('pkg_resources').declare_namespace('kolejka')

import subprocess

from .http_socket import HTTPUnixServer, HTTPUnixConnection
from .parse import parse_time, parse_memory
from .parse import unparse_time, unparse_memory
from .task import KolejkaTask, KolejkaResult

def silent_call(*args, **kwargs):
    kwargs['stdin'] = kwargs.get('stdin', subprocess.DEVNULL)
    kwargs['stdout'] = kwargs.get('stderr', subprocess.DEVNULL)
    kwargs['stderr'] = kwargs.get('stdout', subprocess.DEVNULL)
    return subprocess.call(*args, **kwargs)

