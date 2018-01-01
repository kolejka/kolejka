# vim:ts=4:sts=4:sw=4:expandtab

__import__('pkg_resources').declare_namespace('kolejka')

from .cgroups import ControlGroupSystem
from .http_socket import HTTPUnixServer, HTTPUnixConnection
from .parse import TimeAction, MemoryAction

from .config import KolejkaConfig, kolejka_config, client_config, foreman_config, worker_config
from .limits import KolejkaLimits, KolejkaStats
from .task import KolejkaTask, KolejkaResult
