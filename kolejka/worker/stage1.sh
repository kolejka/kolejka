#!/bin/sh
# vim:ts=4:sts=4:sw=4:expandtab

cd task
ln -s ../result result
exec python3 ../stage2.py . ../result
