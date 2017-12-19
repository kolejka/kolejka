#!/bin/sh
# vim:ts=4:sts=4:sw=4:expandtab

for package in KolejkaCommon KolejkaObserver KolejkaWorker; do
    wheel="dist/${package}-1-py3-none-any.whl"
    if [ -r "${wheel}" ]; then
        python3 -m pip install "${wheel}"
    fi
done

cd task
ln -s ../result result
exec kolejka-worker --stage 2 --task . --result ../result "$@"
