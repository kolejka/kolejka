#!/usr/bin/env python3
# vim:ts=4:sts=4:sw=4:expandtab

import glob
import os
import shutil
import subprocess

DISTRO='DEBIANDISTRO'
DISTROS=['focal', 'jammy']

if os.path.exists('deb_dist'):
    shutil.rmtree('deb_dist')
subprocess.check_call(['./setup.py', '--command-packages=stdeb.command', 'sdist_dsc', '--with-python2=False', '--with-python3=True', '--maintainer', 'kolejka.matinf.uj.edu.pl <kolejka@matinf.uj.edu.pl>', '--suite', DISTRO, '--debian-version', DISTRO ])

for f in glob.glob('deb_dist/*'+DISTRO+'*'):
    try:
        shutil.rmtree(f)
    except:
        os.unlink(f)

for f in glob.glob('deb_dist/*/debian'):
    if os.path.isdir('debian'):
        subprocess.check_call(['rsync', '-a', 'debian/', f])
    shutil.move(f, 'temp_debian')
    for distro in DISTROS:
        subprocess.check_call(['rsync', '-a', 'temp_debian/', f])
        subprocess.check_call(['find', f, '-type', 'f', '-exec', 'sed', '-i', '{}', '-e', 's|'+DISTRO+'|'+distro+'|g', ';' ])
        subprocess.call(['debuild', '-sa', '-S'], cwd=os.path.dirname(f))
    shutil.rmtree(f)
    shutil.move('temp_debian', f)
