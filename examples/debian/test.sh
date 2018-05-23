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
call cat /etc/lsb-release
call cat /etc/os-release
call dpkg -l
call env
call ls -AlR
