#!/usr/bin/env python3
# vim:ts=4:sts=4:sw=4:expandtab

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import venv


parser = argparse.ArgumentParser()
parser.add_argument('--wheel', type=Path, action='append', default=[], help='Wheel to include')
parser.add_argument('--pip', type=str, action='append', default=[], help='PIP package to include')
parser.add_argument('--main', type=str, help='Main function')
parser.add_argument('result', type=Path, help='Result')
args = parser.parse_args()

args.wheel = [ wheel.resolve() for wheel in args.wheel ]
args.result = args.result.resolve()
for wheel in args.wheel:
    assert wheel.is_file()
assert len(args.wheel) + len(args.pip) > 0

wheels = set([ str(wheel.name).split('-')[0] for wheel in args.wheel ])
pips = set([ str(pip).split('=<>')[0] for pip in args.pip ])

with tempfile.TemporaryDirectory() as work_dir:
    wheel_dir = Path(work_dir) / 'wheel'
    wheel_dir.mkdir()
    for wheel in args.wheel[1:]:
        subprocess.run(['unzip', '-q', '-o', str(wheel)], cwd=wheel_dir, check=True)
    subprocess.run(['unzip', '-q', '-o', str(args.wheel[0])], cwd=wheel_dir, check=True)
    requires = set()
    for meta in wheel_dir.glob('*.dist-info/METADATA'):
        with meta.open() as meta_file:
            for line in meta_file:
                require = re.match(r'Requires-Dist: (?P<require>.*)', line)
                if require:
                    require = require.group('require')
                    req = require.split('=<>')[0]
                    if req not in wheels and req not in pips :
                        requires.add(require)
    for element in wheel_dir.glob('*.pth'):
        os.unlink(element)
    for element in wheel_dir.glob('*.dist-info'):
        shutil.rmtree(element)
    subprocess.run(['unzip', '-q', '-o', str(args.wheel[0])], cwd=wheel_dir, check=True)
    for pip in args.pip:
        requires.add(pip)
    print(args.wheel, wheels, requires, args.pip)

    pip_dir = Path(work_dir) / 'pip'
    pip_dir.mkdir()
    for require in requires:
        subprocess.run(['pip3', 'download', require], cwd=pip_dir, check=True)
    extracted_dir = Path(work_dir) / 'extracted'
    extracted_dir.mkdir()
    for whl in pip_dir.glob('*.whl'):
        subprocess.run(['unzip', str(whl)], cwd=extracted_dir, check=True)
    for glob in [ '*.pth', '*.dist-info', '*setuptools*', '*distutils*', '*pkg_resources*', '*docutils*' ]:
        for element in extracted_dir.glob(glob):
            if element.is_file():
                os.unlink(element)
            else:
                shutil.rmtree(element)

    result_dir = Path(work_dir) / 'result'
    result_dir.mkdir()
    subprocess.run(['rsync', '-a', str(extracted_dir)+'/', '--exclude', '*.so', str(result_dir)], cwd=work_dir, check=True)
    subprocess.run(['rsync', '-a', str(wheel_dir)+'/', str(result_dir)], cwd=work_dir, check=True)
    with ( result_dir / '__main__.py' ).open('w') as main_file:
        pkg = '.'.join(args.main.split('.')[:-1])
        fun = args.main.split('.')[-1]
        main_file.write(f'''
if __name__ == '__main__':
    from {pkg} import {fun}
    {fun}()
''')
    first = Path(work_dir) / 'first.zip'
    subprocess.run(['zip', '-q', '-9', str(first), '-r', '.'], cwd=result_dir, check=True)
    second = Path(work_dir) / 'second.zip'
    with second.open('wb') as second_file:
        second_file.write(bytes('#!/usr/bin/env python3\n', 'utf-8'))
        with first.open('rb') as first_file:
            second_file.write(first_file.read())
    shutil.move(second, args.result)
    args.result.chmod(0o755)
