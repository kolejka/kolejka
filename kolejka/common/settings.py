# vim:ts=4:sts=4:sw=4:expandtab

import os
import sys
assert sys.version_info >= (3, 7)
sys.path = [ path for path in sys.path if not os.path.isfile(os.path.join(path, '__nonpath__.py')) ]

CONFIG_APP_NAME = 'kolejka'

CONFIG_APP_AUTHOR = 'kolejka'

CONFIG_FILE = 'kolejka.conf'

CONFIG_SERVER = 'https://kolejka.matinf.uj.edu.pl/kolejka'

OBSERVER_CGROUPS = [ 'memory', 'cpuacct', 'pids', 'perf_event', 'blkio', 'cpuset', 'freezer' ]

OBSERVER_PID_FILE = '/var/run/kolejka/observer/pid'

OBSERVER_SERVERSTRING = 'Kolejka Observer Daemon'

OBSERVER_SOCKET = '/var/run/kolejka/observer/socket'

TASK_SPEC = 'kolejka_task.json'

RESULT_SPEC = 'kolejka_result.json'

WORKER_DIRECTORY = '/var/lib/kolejka'

WORKER_HOSTNAME = 'kolejka'

WORKER_PYTHON_VOLUME = 'kolejka_python'

WORKER_RESERVED_DISK_NAME = '.__reserved_disk_space__'

WORKER_RESERVED_DISK_SIZE = 1024*1024

FOREMAN_CONCURENCY = 8

FOREMAN_INTERVAL = 10
