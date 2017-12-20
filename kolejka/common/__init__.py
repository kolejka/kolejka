# vim:ts=4:sts=4:sw=4:expandtab

__import__('pkg_resources').declare_namespace('kolejka')

from .http_socket import HTTPUnixServer, HTTPUnixConnection
from .limits import KolejkaLimits, KolejkaStats
from .task import KolejkaTask, KolejkaResult
