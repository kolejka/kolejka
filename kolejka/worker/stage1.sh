#!/bin/sh
# vim:ts=4:sts=4:sw=4:expandtab

DEBUG=0
VERBOSE=0

for cmd in "$@"; do
    if [ "${cmd}" = "--debug" ]; then
        DEBUG=1
        VERBOSE=1
    elif [ "${cmd}" = "--verbose" ]; then
        VERBOSE=1
    fi
done

if [ "${VERBOSE}" = "1" ]; then
    echo "Executing stage2" >/dev/stderr
fi

exec ./python3/python3 stage2.py "$@"
