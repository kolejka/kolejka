#!/bin/bash
OFFICE="$(dirname "$(readlink -f "$(which "${0}")")")"

pushd "${OFFICE}/packages" >/dev/null 2>&1
python3 setup.py develop
popd
