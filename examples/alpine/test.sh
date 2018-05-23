#!/bin/sh

echo "###############"
echo "KOLEJKA EXAMPLE"
echo "System: $(whoami)@$(hostname):$(pwd)"
echo "Date: $(date)"
echo "###############"
echo ""

call() {
    echo "#>" "$@"
    "$@"
    echo ""
}

call uname -a
call cat /etc/alpine-release
call cat /etc/os-release
call apk info
call env
call ls -AlR
