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
from threading import Thread
import time
import uuid

from kolejka.common import kolejka_config, foreman_config
from kolejka.common import KolejkaTask, KolejkaResult, KolejkaLimits
from kolejka.common import MemoryAction, TimeAction
from kolejka.client import KolejkaClient
from kolejka.worker.stage0 import stage0

def foreman_single(temp_path, client, task):
    config = foreman_config()
    with tempfile.TemporaryDirectory(temp_path) as jailed_path:
        if task.limits.storage is not None:
            subprocess.run(['mount', '-t', 'tmpfs', '-o', 'size='+str(task.limits.storage), 'none', jailed_path], check=True)
        try:
            task_path = os.path.join(jailed_path, 'task')
            result_path = os.path.join(jailed_path, 'result')
            temp_path = os.path.join(jailed_path, 'temp')
            os.makedirs(task_path, exist_ok=True)
            os.makedirs(result_path, exist_ok=True)
            os.makedirs(temp_path, exist_ok=True)
            task.path = task_path
            client.task_get(task.id, task_path)
            for k,f in task.files.items():
                f.path = k
            task.commit()
            stage0(task.path, result_path, temp_path=temp_path, consume_task_folder=True)
            result = KolejkaResult(result_path)
            result.tags = config.tags
            client.result_put(result)
        finally:
            if task.limits.storage is not None:
                subprocess.run(['umount', '-l', jailed_path])

def foreman():
    config = foreman_config()
    limits = KolejkaLimits()
    limits.cpus = config.cpus
    limits.memory = config.memory
    limits.pids = config.pids
    limits.storage = config.storage
    limits.time = config.time
    limits.network = config.network
    client = KolejkaClient()
    while True:
        try:
            tasks = client.dequeue(config.concurency, limits, config.tags)
            if len(tasks) == 0:
                time.sleep(config.interval)
            else:
                while len(tasks) > 0:
                    resources = KolejkaLimits()
                    resources.update(limits)
                    processes = list()
                    cpus_offset = 0
                    for task in tasks:
                        if len(processes) >= config.concurency:
                            break
                        if task.exclusive and len(processes) > 0:
                            break
                        task.limits.update(limits)
                        task.limits.cpus_offset = cpus_offset
                        ok = True
                        if resources.cpus is not None and task.limits.cpus > resources.cpus:
                            ok = False
                        if resources.memory is not None and task.limits.memory > resources.memory:
                            ok = False
                        if resources.pids is not None and task.limits.pids > resources.pids:
                            ok = False
                        if resources.storage is not None and task.limits.storage > resources.storage:
                            ok = False
                        if ok:
                            proc = Thread(target=foreman_single, args=(config.temp_path, client, task))
                            proc.start()
                            processes.append(proc)
                            cpus_offset += task.limits.cpus
                            if resources.cpus is not None:
                                resources.cpus -= task.limits.cpus
                            if resources.memory is not None:
                                resources.memory -= task.limits.memory
                            if resources.pids is not None:
                                resources.pids -= task.limits.pids
                            if resources.storage is not None:
                                resources.storage -= task.limits.storage
                            tasks = tasks[1:]
                            if task.exclusive:
                                break
                        else:
                            break
                    for proc in processes:
                        proc.join()
        except:
            time.sleep(config.interval)

def config_parser(parser):
    parser.add_argument('--auto-tags', type=bool, help='add automatically generated machine tags', default=True)
    parser.add_argument('--tags', type=str, help='comma separated list of machine tags')
    parser.add_argument('--temp', type=str, help='temp folder')
    parser.add_argument('--interval', type=float, help='dequeue interval (in seconds)')
    parser.add_argument('--concurency', type=int, help='number of simultaneous tasks')
    parser.add_argument('--cpus', type=int, help='cpus limit')
    parser.add_argument('--memory', action=MemoryAction, help='memory limit')
    parser.add_argument('--pids', type=int, help='pids limit')
    parser.add_argument('--storage', action=MemoryAction, help='storage limit')
    parser.add_argument('--time', action=TimeAction, help='time limit')
    parser.add_argument('--network',type=bool, help='allow netowrking')
    def execute(args):
        kolejka_config(args=args)
        foreman()
    parser.set_defaults(execute=execute)
