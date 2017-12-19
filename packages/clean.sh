#!/bin/bash
# vim:ts=4:sts=4:sw=4:expandtab

MYSELF="$(readlink -f "$(which "${0}")")"
OFFICE="$(dirname "${MYSELF}")"
pushd "${OFFICE}" >/dev/null 2>&1

rm -rf dist
rm -rf Kolejka*/deb_dist
rm -rf Kolejka*/dist
rm -rf Kolejka*/build
rm -rf Kolejka*/.eggs
rm -rf Kolejka*/__pycache__
rm -rf Kolejka*/Kolejka*.egg-info
rm -rf Kolejka*/Kolejka*.tar.gz

popd >/dev/null 2>&1
