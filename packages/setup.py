#!/usr/bin/env python3
# vim:ts=4:sts=4:sw=4:expandtab

import re
import os
from setuptools import setup, find_packages

kolejka = {
        'url' : 'https://github.com/kolejka/kolejka',
        'author' : 'KOLEJKA',
        'author_email' : 'kolejka@matinf.uj.edu.pl',
        'long_description' : 'kolejka is a lightweight task scheduling platform developed for a small computational grid at Faculty of Mathematics and Computer Science of the Jagiellonian University in Kraków.',
        'license' : 'MIT',
        'version' : '0.1',
        'python_requires' : '>=3.5',
       'namespace_packages' : [ 'kolejka' ],
    }

from KolejkaCommon.setup import kolejka_common
from KolejkaObserver.setup import kolejka_observer
from KolejkaServer.setup import kolejka_server
from KolejkaClient.setup import kolejka_client
from KolejkaWorker.setup import kolejka_worker
from KolejkaForeman.setup import kolejka_foreman

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

if __name__ == '__main__':
    import datetime
    import subprocess
    import sys
    p = subprocess.Popen(['git', 'show', '-s', '--format=%at'], stdout=subprocess.PIPE)
    s = datetime.datetime.fromtimestamp(int(p.communicate()[0]), datetime.timezone.utc)
    assert p.returncode == 0
    kolejka['version'] += '.'+s.strftime('%Y%m%d%H%M')
    for pkg in all_pkgs:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), pkg['name'], 'setup.cfg'), 'w') as setup_cfg:
            setup = list()
            setup.append('[metadata]')
            for key in [ 'name', 'version', 'url', 'download_url', 'author', 'author_email', 'maintainer', 'maintainer_email', 'classifiers', 'license', 'description', 'long_description', 'long_description_content_type', 'keywords', 'platforms', 'provides', 'requires', 'obsoletes' ]:
                if key in kolejka:
                    val = kolejka[key]
                    if isinstance(val, list):
                        val = ', '.join(val)
                    setup.append('{} = {}'.format(key, val))
            setup.append('[options]')
            for key in [ 'namespace_packages', 'python_requires' ]:
                if key in kolejka:
                    val = kolejka[key]
                    if isinstance(val, list):
                        val = ', '.join(val)
                    setup.append('{} = {}'.format(key, val))
            setup_cfg.writelines([line+'\n' for line in setup])
    for pkg in all_pkgs:
        if pkg['name'] in selected_pkgs:
            subprocess.call(['python3', './setup.py'] + sys.argv[1:], cwd=pkg['name'])
