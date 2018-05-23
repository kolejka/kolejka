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

call g++ --version
call g++ -std=c++17 -pthread -Wall -g -O3 -o example example.cpp
call ./example
