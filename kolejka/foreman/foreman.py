# vim:ts=4:sts=4:sw=4:expandtab

import copy
import datetime
import dateutil.parser
import glob
import json
import logging
import math
from multiprocessing import Process
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

from kolejka.common.settings import FOREMAN_INTERVAL, FOREMAN_CONCURENCY
from kolejka.common import KolejkaTask, KolejkaResult, KolejkaLimits, MemoryAction, TimeAction
from kolejka.client import KolejkaClient
from kolejka.worker.stage0 import stage0

def foreman_single(client, task):
    with tempfile.TemporaryDirectory() as jailed_path:
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
            client.result_put(result)
        finally:
            if task.limits.storage is not None:
                subprocess.run(['umount', '-l', jailed_path])

def foreman(sleep_time, concurency, limits):
    client = KolejkaClient()
    while True:
        tasks = client.dequeue(concurency, limits)
        if len(tasks) == 0:
            time.sleep(sleep_time)
        else:
            while len(tasks) > 0:
                resources = KolejkaLimits()
                resources.update(limits)
                processes = list()
                cpus_offset = 0
                for task in tasks:
                    if len(processes) >= concurency:
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
                        proc = Process(target=foreman_single, args=(client, task))
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
                    else:
                        break
                for proc in processes:
                    proc.join()

def execute(args):
    limits = KolejkaLimits()
    limits.cpus = args.cpus
    limits.memory = args.memory
    limits.pids = args.pids
    limits.storage = args.storage
    limits.time = args.time
    foreman(args.interval, args.concurency, limits)

def config_parser(parser):
    parser.add_argument('--interval', type=float, default=FOREMAN_INTERVAL, help='dequeue interval (in seconds)')
    parser.add_argument('--concurency', type=int, default=FOREMAN_CONCURENCY, help='number of simultaneous tasks')
    parser.add_argument('--cpus', type=int, help='cpus limit')
    parser.add_argument('--memory', action=MemoryAction, help='memory limit')
    parser.add_argument('--pids', type=int, help='pids limit')
    parser.add_argument('--storage', action=MemoryAction, help='storage limit')
    parser.add_argument('--time', action=TimeAction, help='time limit')
    parser.set_defaults(execute=execute)
