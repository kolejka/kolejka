#!/usr/bin/env python3
# vim:ts=4:sts=4:sw=4:expandtab

import os
import re
from setuptools import setup, find_packages

def sub_find_packages(module):
    return [ module ] + [ module + '.' + submodule for submodule in find_packages(re.sub(r'\.', r'/', module)) ]

kolejka_common = {
        'name' : 'KolejkaCommon',
        'description' : 'Kolejka Common',
        'packages' : sub_find_packages('kolejka.common'),
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
