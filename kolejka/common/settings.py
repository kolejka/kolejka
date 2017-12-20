# vim:ts=4:sts=4:sw=4:expandtab

from .limits import KolejkaLimits

OBSERVER_SOCKET = "/var/run/kolejka/observer/socket"

OBSERVER_CGROUPS = [ 'memory', 'cpuacct', 'pids', 'perf_event', 'blkio', 'cpuset', 'freezer' ]

OBSERVER_SERVERSTRING = 'Kolejka Observer Daemon'

TASK_SPEC = 'kolejka_task.json'

RESULT_SPEC = 'kolejka_result.json'

WORKER_LIMITS = KolejkaLimits(pids=16*1024, cpus=8, memory='2G', time='10M')
