#!/usr/bin/env python3
# vim:ts=4:sts=4:sw=4:expandtab

import glob
import os
import subprocess

os.chdir(os.path.dirname(__file__))

for example in [ os.path.dirname(task) for task in glob.glob('*/kolejka_task.json') ] :
    print('Example: '+example)
    result = example+'-result'
    if not os.path.isdir(result):
        subprocess.run(['kolejka-client', 'execute', example, result])
