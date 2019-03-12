#!/bin/sh
EXAMPLE="alpine"

echo "###############"
echo "KOLEJKA EXAMPLE"
echo "System: $(whoami)@$(hostname):$(pwd)"
echo "Date: $(date)"
echo "Example: ${EXAMPLE}"
echo "###############"
echo ""

call() {
    echo "#>" "$@"
    "$@"
    res="$?"
    echo ""
    return "${res}"
}

call uname -a
call cat /etc/alpine-release
call cat /etc/os-release
call apk info
call env
call ls -AlR
