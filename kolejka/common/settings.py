# vim:ts=4:sts=4:sw=4:expandtab

OBSERVER_SOCKET = "/var/run/kolejka/observer/socket"

OBSERVER_CGROUPS = [ 'memory', 'cpuacct', 'pids', 'perf_event', 'blkio', 'cpuset', 'freezer' ]

OBSERVER_SERVERSTRING = 'Kolejka Observer Daemon'
