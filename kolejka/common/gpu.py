# vim:ts=4:sts=4:sw=4:expandtab

from kolejka.common import settings

import re

from .limits import KolejkaStats
from .nvidia import NvidiaSMILog

def gpu_stats(gpus: list = None):
    if gpus is not None:
        gpus = [ int(gpu) for gpu in gpus ]
    stats = KolejkaStats()
    smilog = NvidiaSMILog.from_exec()
    stats.load({ 'gpus' : {
        index : {
            'name': gpu.name,
            'id': gpu.uuid,
            'memory_total': gpu.memory_total,
            'memory_usage': gpu.memory_total - gpu.memory_free,
            'temperature': gpu.temperature,
            'utilization': gpu.utilization,
        } for index, gpu in enumerate(smilog.gpus) if gpus is None or index in gpus
    }})
    return stats

def full_gpuset():
    return list(gpu_stats().gpus.keys())

def limited_gpuset(gpus, gpus_offset):
    gpuset = list()
    if gpus_offset is None:
        gpus_offset = 0
    if not gpus:
        return gpuset
    full = full_gpuset()
    if not len(full):
        return gpuset

    return list(set([
        full[(gpus_offset + _index) % len(full)] for _index in range(gpus)
    ]))
