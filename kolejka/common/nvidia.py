#!/usr/bin/env python3
# vim:ts=4:sts=4:sw=4:expandtab

from kolejka.common import settings

import logging
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

class NvidiaSMILog:
    class GPULog:
        def __init__(self, element=None):
            self.id = element.get('id')
            self.uuid = element.find('uuid').text
            self.name = element.find('product_name').text
            self.brand = element.find('product_brand').text
            self.architecture = element.find('product_architecture').text
            self.temperature = float(element.find('temperature').find('gpu_temp').text.split()[0])
            self.fan_speed = float(element.find('fan_speed').text.split()[0])
            self.performance_state = element.find('performance_state').text
            self.power_draw = float(element.find('power_readings').find('power_draw').text.split()[0])
            self.memory_total = int(float(element.find('fb_memory_usage').find('total').text.split()[0]) * 1024**2)
            self.memory_free = int(float(element.find('fb_memory_usage').find('free').text.split()[0]) * 1024**2)
            self.utilization = float(element.find('utilization').find('gpu_util').text.split()[0]) / 100
        def __repr__(self):
            return f'{self.name} ({self.__dict__})'
    def __init__(self, element=None):
        if element is not None:
            self.driver_version = element.find('driver_version').text
            self.cuda_version = element.find('cuda_version').text
            self.gpus = [ self.GPULog(element) for element in element.findall('gpu') ]
        else:
            self.driver_version = None
            self.cuda_version = None
            self.gpus = list()
    def __repr__(self):
        return f'NVIDIA Cards (@{self.cuda_version}/{self.driver_version}): {self.gpus}'

    @classmethod
    def from_string(cls, string):
        try:
            element = ET.fromstring(string)
        except ET.ParseError:
            logging.warning(f'Failed to parse string. Returning empty log.')
            return cls()
        return cls(element)
    @classmethod
    def from_path(cls, path):
        try:
            with pathlib.Path(path).open() as xml_file:
                try:
                    tree = ET.parse(xml_file)
                    element = tree.getroot()
                except ET.ParseError:
                    logging.warning(f'Failed to parse contents of \'{path}\'. Returning empty log.')
                    return cls()
        except OSError:
            logging.warning(f'Failed to open path \'{path}\'. Returning empty log.')
            return cls()
        return cls(element)
    @classmethod
    def from_exec(cls):
        try:
            result = subprocess.run(['nvidia-smi', '-q', '-x'], capture_output=True)
        except OSError:
            logging.info('Failed to launch nvidia-smi. Returning empty log.')
            return cls()
        if result.returncode != 0:
            logging.info('Launch of nvidia-smi failed. Returning empty log.')
            return cls()
        return cls.from_string(str(result.stdout, 'utf-8'))

if __name__ == '__main__':
    print(NvidiaSMILog.from_exec())
