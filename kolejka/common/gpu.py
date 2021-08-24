import gpustat

from kolejka.common.limits import KolejkaStats

def normalize_name(name: str) -> str:
    return '-'.join(name.lower().split(' ')[1:])

def gpu_stats(gpus: list = None):
    stats = KolejkaStats()
    try:
        query = gpustat.GPUStatCollection.new_query()
        stats.load({ 'gpus' : {
            str(index) : {
                'name': gpu.name,
                'id': normalize_name(gpu.name),
                'memory_total': gpu.memory_total * 1024 * 1024,
                'memory_usage': gpu.memory_total * 1024 * 1024 - gpu.memory_free * 1024 * 1024,
                'temperature': gpu.temperature,
                'utilization': gpu.utilization
            } for index, gpu in enumerate(query.gpus) if gpus is None or str(index) in gpus
        }})
    except:
        pass
    return stats

def full_gpuset():
    query = gpustat.GPUStatCollection.new_query()
    return list(range(len(query.gpus)))

def limited_gpuset(full, gpus, gpus_offset):
    if gpus_offset is None:
        gpus_offset = 0

    return [
        str((gpus_offset + _index) % len(full)) for _index in range(gpus)
    ]
