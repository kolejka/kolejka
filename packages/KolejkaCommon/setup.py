#!/usr/bin/env python3
# vim:ts=4:sts=4:sw=4:expandtab

import os
import re
from setuptools import setup, find_namespace_packages

kolejka_common = {
        'name' : 'KolejkaCommon',
        'description' : 'Kolejka Common',
        'packages' : find_namespace_packages(include=['kolejka.*']),
        'install_requires' : [
            'appdirs',
            'setproctitle',
            'gpustat==0.6.0',
        ],
        'entry_points' : {
            'console_scripts' : [
                'kolejka = kolejka.common:main',
            ],
        },
    }

if __name__ == '__main__':
    assert os.path.isfile(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'setup.cfg'))
    setup(**kolejka_common)
