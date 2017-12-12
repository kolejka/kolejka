# vim:ts=4:sts=4:sw=4:expandtab

__import__('pkg_resources').declare_namespace('kolejka')

from .http_socket import HTTPUnixServer, HTTPUnixConnection
from .parse import parse_time, parse_memory
