#!/bin/sh
# vim:ts=4:sts=4:sw=4:expandtab

echo "Executing stage2" >/dev/stderr
exec python3 stage2.py "$@"
