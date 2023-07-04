# vim:ts=4:sts=4:sw=4:expandtab

from kolejka.common import settings

import copy
import datetime
import dateutil.parser
import glob
import json
import logging
import math
from multiprocessing import Process
import os
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile
import traceback
from threading import Thread
import time
import uuid

from kolejka.common import kolejka_config, foreman_config
from kolejka.common import KolejkaTask, KolejkaResult, KolejkaLimits
from kolejka.common import MemoryAction, TimeAction, BigIntAction
from kolejka.client import KolejkaClient
from kolejka.common.gpu import gpu_stats
from kolejka.common.images import (
    pull_docker_image,
    get_docker_image_size,
    check_docker_image_existance,
    list_docker_images,
    remove_docker_image
)
from kolejka.worker.stage0 import stage0
from kolejka.worker.volume import check_python_volume

def system_reset():
    with pathlib.Path('/proc/sysrq-trigger').open('wb') as sysrq_trigger:
        sysrq_trigger.write(b'b')

def manage_images(pull, size, necessary_images, priority_images):
    necessary_size = sum(necessary_images.values(), 0)
    free_size = size - necessary_size
    assert free_size >= 0
    docker_images = list_docker_images()
    p_images = dict()
    for image in priority_images:
        if image in docker_images:
            p_images[image] = docker_images[image]
    priority_images = p_images
    keep_images = set()
    for image in necessary_images:
        keep_images.add(image)
    list_images = list(priority_images.items())
    random.shuffle(list_images)
    li = list(docker_images.items())
    random.shuffle(li)
    list_images += li
    for image,size in list_images:
        if image in keep_images:
            continue
        if size <= free_size:
            free_size -= size
            keep_images.add(image)
    for image in docker_images:
        if image not in keep_images:
            remove_docker_image(image)
    for image, size in necessary_images.items():
        pull_image = pull
        if not pull_image:
            if not check_docker_image_existance(image):
                pull_image = True 
        if pull_image:
            pull_docker_image(image)
        image_size = get_docker_image_size(image)
        assert image_size <= size

def foreman_single(temp_path, task, task_timeout=-1):
    config = foreman_config()
    with tempfile.TemporaryDirectory(temp_path) as jailed_path:
        if task.limits.workspace is not None:
            subprocess.run(['mount', '-t', 'tmpfs', '-o', 'size='+str(task.limits.workspace), 'none', jailed_path], check=True)
        try:
            task_path = os.path.join(jailed_path, 'task')
            result_path = os.path.join(jailed_path, 'result')
            temp_path = os.path.join(jailed_path, 'temp')
            os.makedirs(task_path, exist_ok=True)
            os.makedirs(result_path, exist_ok=True)
            os.makedirs(temp_path, exist_ok=True)
            task.path = task_path
            client = KolejkaClient()
            client.task_get(task.id, task_path)
            for k,f in task.files.items():
                f.path = k
            task.commit()
            stage0_timeout = task_timeout
            stage0_run = Thread(target=stage0, args=(task.path, result_path), kwargs={'temp_path':temp_path, 'consume_task_folder':True})
            stage0_run.start()
            stage0_run.join(timeout=stage0_timeout)
            if stage0_run.is_alive():
                #TODO: Report problem to kolejka-server?
                system_reset()
            else:
                result = KolejkaResult(result_path)
                result.tags = config.tags
                client.result_put(result)
        except:
            traceback.print_exc()
        finally:
            if task.limits.storage is not None:
                subprocess.run(['umount', '-l', jailed_path])

def foreman():
    config = foreman_config()
    gstats = gpu_stats().gpus
    limits = KolejkaLimits()
    limits.cpus = config.cpus
    limits.memory = config.memory
    limits.swap = config.swap
    limits.pids = config.pids
    limits.storage = config.storage
    limits.image = config.image
    limits.workspace = config.workspace
    limits.time = config.time
    limits.network = config.network
    limits.gpus = config.gpus
    limits.perf_instructions = config.perf_instructions
    limits.perf_cycles = config.perf_cycles
    limits.cgroup_depth = config.cgroup_depth
    limits.cgroup_descendants = config.cgroup_descendants
    if limits.gpus is None:
        limits.gpus = len(gstats)
    limits.gpu_memory = config.gpu_memory
    for k,v in gstats.items():
        if limits.gpu_memory is None:
            limits.gpu_memory = v.memory_total
        elif v.memory_total is not None:
            limits.gpu_memory = min(limits.gpu_memory, v.memory_total)
    client = KolejkaClient()
    logging.debug(f'Foreman tags: {config.tags}, limits: {limits.dump()}')
    while True:
        try:
            tasks = client.dequeue(config.concurency, limits, config.tags)
            if len(tasks) == 0:
                time.sleep(config.interval)
            else:
                check_python_volume()
                while len(tasks) > 0:
                    resources = KolejkaLimits()
                    resources.copy(limits)
                    image_usage = dict()
                    children_args = list()
                    cpus_offset = 0
                    gpus_offset = 0
                    tasks_timeout = None

                    for task in tasks:
                        if len(children_args) >= config.concurency:
                            break
                        if task.exclusive and len(children_args) > 0:
                            break
                        task.limits.update(limits)
                        task.limits.cpus_offset = cpus_offset
                        task.limits.gpus_offset = gpus_offset
                        ok = True
                        if resources.cpus is not None and task.limits.cpus > resources.cpus:
                            ok = False
                        if task.limits.gpus is not None and task.limits.gpus > 0:
                            if resources.gpus is None or task.limits.gpus > resources.gpus:
                                ok = False
                            if resources.gpu_memory is not None and task.limits.gpu_memory > resources.gpu_memory:
                                ok = False
                        if resources.memory is not None and task.limits.memory > resources.memory:
                            ok = False
                        if resources.swap is not None and task.limits.swap > resources.swap:
                            ok = False
                        if resources.pids is not None and task.limits.pids > resources.pids:
                            ok = False
                        if resources.storage is not None and task.limits.storage > resources.storage:
                            ok = False
                        if resources.image is not None:
                            image_usage_add = max(image_usage.get(task.image, 0), task.limits.image) - image_usage.get(task.image, 0)
                            if image_usage_add > resources.image:
                                ok = False
                        if resources.workspace is not None and task.limits.workspace > resources.workspace:
                            ok = False
                        if resources.perf_instructions is not None and task.limits.perf_instructions > resources.perf_instructions:
                            ok = False
                        if resources.perf_cycles is not None and task.limits.perf_cycles > resources.perf_cycles:
                            ok = False
                        if resources.cgroup_depth is not None and task.limits.cgroup_depth > resources.cgroup_depth:
                            ok = False
                        if resources.cgroup_descendants is not None and task.limits.cgroup_descendants > resources.cgroup_descendants:
                            ok = False
                        if ok:
                            children_args.append([config.temp_path, task])
                            cpus_offset += task.limits.cpus
                            if resources.cpus is not None:
                                resources.cpus -= task.limits.cpus
                            if resources.gpus is not None and task.limits.gpus is not None:
                                resources.gpus -= task.limits.gpus
                                gpus_offset += task.limits.gpus
                            if resources.memory is not None:
                                resources.memory -= task.limits.memory
                            if resources.swap is not None:
                                resources.swap -= task.limits.swap
                            if resources.pids is not None:
                                resources.pids -= task.limits.pids
                            if resources.storage is not None:
                                resources.storage -= task.limits.storage
                            if resources.image is not None:
                                resources.image -= image_usage_add
                                image_usage[task.image] = max(image_usage.get(task.image, 0), task.limits.image)
                            if resources.workspace is not None:
                                resources.workspace -= task.limits.workspace
                            if resources.perf_instructions is not None:
                                resources.perf_instructions -= task.limits.perf_instructions
                            if resources.perf_cycles is not None:
                                resources.perf_cycles -= task.limits.perf_cycles
                            if resources.cgroup_descendants is not None:
                                resources.cgroup_descendants -= task.limits.cgroup_descendants
                            if task.limits.time is None:
                                tasks_timeout = -1
                            else:
                                if tasks_timeout is None:
                                    tasks_timeout = task.limits.time.total_seconds()
                                else:
                                    tasks_timeout = max(task.limits.time.total_seconds(), tasks_timeout)
                            tasks = tasks[1:]
                            if task.exclusive:
                                break
                        else:
                            break
                    if config.image is not None:
                        manage_images(
                            config.pull,
                            config.image,
                            image_usage,
                            [task.image for task in tasks]
                        )
                    if tasks_timeout is not None and tasks_timeout >= 0:
                        tasks_timeout = 10 + 2*tasks_timeout
                    children = list()
                    for args in children_args:
                        args.append(tasks_timeout)
                        process = Process(target=foreman_single, args=args)
                        children.append(process)
                        process.start()
                    for process in children:
                        process.join()
        except KeyboardInterrupt:
            raise
        except:
            traceback.print_exc()
            time.sleep(config.interval)

def config_parser(parser):
    parser.add_argument('--auto-tags', type=bool, help='add automatically generated machine tags', default=True)
    parser.add_argument('--pull', action='store_true', help='always pull images, even if local version is present', default=False)
    parser.add_argument('--tags', type=str, help='comma separated list of machine tags')
    parser.add_argument('--temp', type=str, help='temp folder')
    parser.add_argument('--interval', type=float, help='dequeue interval (in seconds)')
    parser.add_argument('--concurency', type=int, help='number of simultaneous tasks')
    parser.add_argument('--cpus', type=int, help='cpus limit')
    parser.add_argument('--memory', action=MemoryAction, help='memory limit')
    parser.add_argument('--swap', action=MemoryAction, help='swap limit')
    parser.add_argument('--pids', type=int, help='pids limit')
    parser.add_argument('--storage', action=MemoryAction, help='storage limit')
    parser.add_argument('--image', action=MemoryAction, help='image size limit')
    parser.add_argument('--workspace', action=MemoryAction, help='workspace size limit')
    parser.add_argument('--time', action=TimeAction, help='time limit')
    parser.add_argument('--network', type=bool, help='allow netowrking')
    parser.add_argument('--gpus', type=int, help='gpus limit')
    parser.add_argument('--gpu-memory', type=MemoryAction, help='gpu memory limit')
    parser.add_argument('--perf-instructions', type=BigIntAction, help='CPU instructions limit')
    parser.add_argument('--perf-cycles', type=BigIntAction, help='CPU cycles limit')
    parser.add_argument('--cgroup-depth', type=int, help='Cgroup depth limit')
    parser.add_argument('--cgroup-descendants', type=int, help='Cgroup descendants limit')
    def execute(args):
        kolejka_config(args=args)
        foreman()
    parser.set_defaults(execute=execute)
