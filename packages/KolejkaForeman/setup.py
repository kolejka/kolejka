#!/usr/bin/env python3
# vim:ts=4:sts=4:sw=4:expandtab

import os
import re
from setuptools import setup, find_packages

def sub_find_packages(module):
    return [ module ] + [ module + '.' + submodule for submodule in find_packages(re.sub(r'\.', r'/', module)) ]

kolejka = {
        'url' : 'https://github.com/kolejka/kolejka',
        'author' : 'KOLEJKA',
        'author_email' : 'kolejka@matinf.uj.edu.pl',
        'long_description' : 'kolejka is a lightweight task scheduling platform developed for a small computational grid at Faculty of Mathematics and Computer Science of the Jagiellonian University in Kraków.',
        'license' : 'MIT',
        'version' : '0.1',
        'python_requires' : '>=3.0',
        'namespace_packages' : [ 'kolejka' ],
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

if __name__ == '__main__':
    kolejka_foreman.update(kolejka)
    setup(**kolejka_foreman)
