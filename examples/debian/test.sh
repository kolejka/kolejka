#!/bin/sh
EXAMPLE="debian"

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
call cat /etc/lsb-release
call cat /etc/os-release
call dpkg -l
call env
call ls -AlR
