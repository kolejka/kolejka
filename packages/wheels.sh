#!/bin/bash
# vim:ts=4:sts=4:sw=4:expandtab

MYSELF="$(readlink -f "$(which "${0}")")"
OFFICE="$(dirname "${MYSELF}")"
pushd "${OFFICE}" >/dev/null 2>&1

mkdir -p dist

python3 ./setup.py --no-user-cfg bdist_wheel
find Kolejka*/dist -type f -name "*.whl" -exec cp -a {} dist ";"

popd >/dev/null 2>&1
