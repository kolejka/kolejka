# vim:ts=4:sts=4:sw=4:expandtab

OBSERVER_SOCKET = "/var/run/kolejka/observer/socket"

OBSERVER_CGROUPS = [ 'memory', 'cpuacct', 'pids', 'perf_event', 'blkio', 'cpuset', 'freezer' ]

OBSERVER_SERVERSTRING = 'Kolejka Observer Daemon'

TASK_SPEC = 'kolejka_task.json'

RESULT_SPEC = 'kolejka_result.json'

WORKER_HOSTNAME = 'kolejka'

WORKER_REPOSITORY = 'kolejka.matinf.uj.edu.pl'

WORKER_DIRECTORY = '/opt/kolejka'
