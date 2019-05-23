#!/bin/sh
EXAMPLE="timebomb"

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
    echo "?>" "${res}"
    echo ""
    return "${res}"
}

call g++ --version
call g++ -std=c++17 -pthread -Wall -g -O3 -o example example.cpp
call ./example
