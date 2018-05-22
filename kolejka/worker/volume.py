# vim:ts=4:sts=4:sw=4:expandtab

import copy
import datetime
import dateutil.parser
import glob
import json
import logging
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

from kolejka.common.settings import WORKER_PYTHON_VOLUME

def silent_call(*args, **kwargs):
    kwargs['stdin'] = kwargs.get('stdin', subprocess.DEVNULL)
    kwargs['stdout'] = kwargs.get('stderr', subprocess.DEVNULL)
    kwargs['stderr'] = kwargs.get('stdout', subprocess.DEVNULL)
    return subprocess.run(*args, **kwargs)

def create_python_volume():
    docker_call = [ 'docker', 'volume', 'create', WORKER_PYTHON_VOLUME ];
    subprocess.run(docker_call)
    docker_call = [ 'docker', 'run', '--rm' ]
    docker_call += [ '--volume', '{}:{}:{}'.format(WORKER_PYTHON_VOLUME, '/kolejka_python', 'rw') ]
    for spath in [ os.path.dirname(__file__) ]:
        create = os.path.join(spath, 'create_alpine_python3_volume.sh')
        if os.path.isfile(create):
            docker_call += [ '--volume', '{}:{}:{}'.format(os.path.realpath(create), '/kolejka_python.sh', 'ro') ]
    docker_call += [ 'alpine:latest', '/bin/sh', '/kolejka_python.sh' ]
    subprocess.run(docker_call)

def check_python_volume():
    try:
        docker_run = subprocess.run(['docker', 'volume', 'inspect', '--format', '{{json .Name}}', WORKER_PYTHON_VOLUME], stdout=subprocess.PIPE)
        state = json.loads(str(docker_run.stdout, 'utf-8'))
        if state == WORKER_PYTHON_VOLUME:
            return
        print(state)
    except:
        pass
    create_python_volume()

def config_parser(parser):
    def execute(args):
        create_python_volume()
    parser.set_defaults(execute=execute)
