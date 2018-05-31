# vim:ts=4:sts=4:sw=4:expandtab

CONFIG_APP_NAME = 'kolejka'

CONFIG_APP_AUTHOR = 'kolejka'

CONFIG_FILE = 'kolejka.conf'

CONFIG_SERVER = 'https://kolejka.matinf.uj.edu.pl/kolejka'

OBSERVER_CGROUPS = [ 'memory', 'cpuacct', 'pids', 'perf_event', 'blkio', 'cpuset', 'freezer' ]

OBSERVER_PID_FILE = "/var/run/kolejka/observer/pid"

OBSERVER_SERVERSTRING = 'Kolejka Observer Daemon'

OBSERVER_SOCKET = "/var/run/kolejka/observer/socket"

TASK_SPEC = 'kolejka_task.json'

RESULT_SPEC = 'kolejka_result.json'

WORKER_DIRECTORY = '/var/lib/kolejka'

WORKER_HOSTNAME = 'kolejka'

WORKER_PYTHON_VOLUME = 'kolejka_python'

FOREMAN_CONCURENCY = 8

FOREMAN_INTERVAL = 10
