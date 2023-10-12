#!/bin/bash
# vim:ts=4:sts=4:sw=4:expandtab

MYSELF="$(readlink -f "$(which "${0}")")"
OFFICE="$(dirname "${MYSELF}")"
pushd "${OFFICE}" >/dev/null 2>&1

rm -rf dist
mkdir -p dist

python3 ./setup.py --no-user-cfg sdist bdist_wheel
find Kolejka*/dist -type f -name "*.whl" -exec cp -a {} dist ";"

for i in Kolejka* ; do
    pushd "${i}"
    ./debian.py
    popd
done
find Kolejka*/deb_dist -type f -name "*.deb" -exec cp -a {} dist ";"
find Kolejka*/deb_dist -type f -name "*.dsc" -exec cp -a {} dist ";"
find Kolejka*/deb_dist -type f -name "*.orig.tar.gz" -exec cp -a {} dist ";"
find Kolejka*/deb_dist -type f -name "*.debian.tar.xz" -exec cp -a {} dist ";"
find Kolejka*/deb_dist -type f -name "*_source.changes" -exec cp -a {} dist ";"
find Kolejka*/deb_dist -type f -name "*_source.buildinfo" -exec cp -a {} dist ";"
find dist -type f -name "*_source.changes" -exec debsign --no-conf "-mkolejka.matinf.uj.edu.pl <kolejka@matinf.uj.edu.pl>" --re-sign -S {} ";"

kolejka_common_wheel="$(find dist -name "KolejkaCommon-*.whl" |sort |tail -n 1)"
kolejka_client_wheel="$(find dist -name "KolejkaClient-*.whl" |sort |tail -n 1)"

./wheel_executable.py --wheel "${kolejka_client_wheel}" --wheel "${kolejka_common_wheel}" --main kolejka.client.main  dist/kolejka-client

popd >/dev/null 2>&1
