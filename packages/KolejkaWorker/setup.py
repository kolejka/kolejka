#!/usr/bin/env python3
# vim:ts=4:sts=4:sw=4:expandtab

import os
import re
from setuptools import setup, find_namespace_packages

kolejka_worker = {
        'name' : 'KolejkaWorker',
        'description' : 'Kolejka Worker',
        'packages' : find_namespace_packages(include=['kolejka.*']),
        'install_requires' : [
            'python-dateutil',
            'setproctitle',
            'KolejkaCommon',
            'KolejkaObserver',
        ],
        'package_data' : {
            'kolejka.worker' : [ '*.sh' ],
        },
        'entry_points' : {
            'console_scripts' : [
                'kolejka-worker = kolejka.worker:main',
            ],
        },
    }

if __name__ == '__main__':
    assert os.path.isfile(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'setup.cfg'))
    setup(**kolejka_worker)
