#!/bin/bash
# vim:ts=4:sts=4:sw=4:expandtab

MYSELF="$(readlink -f "$(which "${0}")")"
OFFICE="$(dirname "${MYSELF}")"
pushd "${OFFICE}" >/dev/null 2>&1

for i in Kolejka*; do cd "$i"; ./setup.py bdist_wheel upload; cd ..; done

find dist -type f -name "*_source.changes" -exec debsign --no-conf "-mkolejka.matinf.uj.edu.pl <kolejka@matinf.uj.edu.pl>" --re-sign -S {} ";"
find dist -type f -name "*_source.changes" -exec dput ppa:kolejka/kolejka {} ";"

popd >/dev/null 2>&1
