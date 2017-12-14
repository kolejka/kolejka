#!/bin/bash
# vim:ts=4:sts=4:sw=4:expandtab

for i in Kolejka*; do cd "$i"; ./setup.py bdist_wheel upload; cd ..; done

find dist -type f -name "*_source.changes" -exec debsign --no-conf "-mkolejka.matinf.uj.edu.pl <kolejka@matinf.uj.edu.pl>" --re-sign -S {} ";"
find dist -type f -name "*_source.changes" -exec dput ppa:kolejka/kolejka {} ";"
