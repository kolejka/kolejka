#!/usr/bin/env python3
# vim:ts=4:sts=4:sw=4:expandtab

import re
import os
from setuptools import setup, find_packages

def sub_find_packages(module):
    return [ module ] + [ module + '.' + submodule for submodule in find_packages(re.sub(r'\.', r'/', module)) ]

kolejka = {
        'url' : 'https://github.com/kolejka/kolejka',
        'author' : 'KOLEJKA',
        'author_email' : 'kolejka@matinf.uj.edu.pl',
        'license' : 'MIT',
        'version' : '0.1',
        'python_requires' : '>=3.0',
        'zip_safe' : False,
        'namespace_packages' : [ 'kolejka' ],
    }

kolejka_common = {
        'name' : 'KolejkaCommon',
        'description' : 'Kolejka Common',
        'packages' : sub_find_packages('kolejka.common'),
    }

kolejka_observer = {
        'name' : 'KolejkaObserver',
        'description' : 'Kolejka Observer Daemon',
        'packages' : sub_find_packages('kolejka.observer'),
        'install_requires' : [
            'KolejkaCommon',
        ],
        'entry_points' : {
            'console_scripts' : [
                'kolejka-observer = kolejka.observer.server:main',
            ],
        },
    }

kolejka_server = {
        'name' : 'KolejkaServer',
        'description' : 'Kolejka Server',
        'packages' : sub_find_packages('kolejka.server'),
        'install_requires' : [
            'django',
            'psycopg2',
            'KolejkaCommon',
        ],
        'entry_points' : {
            'console_scripts' : [
                'kolejka-server = kolejka.server:main',
            ],
        },
    }

kolejka_client = {
        'name' : 'KolejkaClient',
        'description' : 'Kolejka Client',
        'packages' : sub_find_packages('kolejka.client'),
        'install_requires' : [
            'KolejkaCommon',
        ],
        'entry_points' : {
            'console_scripts' : [
                'kolejka-client = kolejka.client:main',
            ],
        },
    }

kolejka_worker = {
        'name' : 'KolejkaWorker',
        'description' : 'Kolejka Worker',
        'packages' : sub_find_packages('kolejka.worker'),
        'install_requires' : [
            'KolejkaCommon',
            'KolejkaObserver',
        ],
        'entry_points' : {
            'console_scripts' : [
                'kolejka-worker = kolejka.worker:main',
            ],
        },
    }

kolejka_foreman = {
        'name' : 'KolejkaForeman',
        'description' : 'Kolejka Foreman',
        'packages' : sub_find_packages('kolejka.foreman'),
        'install_requires' : [
            'KolejkaCommon',
            'KolejkaWorker',
            'KolejkaClient',
        ],
        'entry_points' : {
            'console_scripts' : [
                'kolejka-foreman = kolejka.foreman:main',
            ],
        },
    }

all_pkgs = [ kolejka_common, kolejka_observer, kolejka_server, kolejka_client, kolejka_worker, kolejka_foreman ]
all_pkgs_names = [ pkg['name'] for pkg in all_pkgs ]
selected_pkgs = set()
for system in [ s.strip() for s in os.environ.get('KOLEJKA_SYSTEMS', '').split(', ') ]:
    if system.lower().startswith('kolejka'):
        system = system[len('kolejka'):]
    if system:
        system = 'Kolejka'+system.title()
        if system in all_pkgs_names:
            selected_pkgs.add(system)
if len(selected_pkgs) == 0:
    selected_pkgs = set(all_pkgs_names)

for pkg in reversed(all_pkgs):
    pkg.update(kolejka)
    if pkg['name'] in selected_pkgs:
       for dep in pkg.get('install_requires', []):
           selected_pkgs.add(dep)

for pkg in all_pkgs:
    if pkg['name'] in selected_pkgs:
        setup(**pkg)
