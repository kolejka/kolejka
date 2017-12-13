.PHONY: all
all: python debian

.PHONY: python
python:
	python3 ./setup.py --no-user-cfg sdist bdist_wheel
	mkdir -p dist
	find Kolejka*/dist -type f -name "*.whl" -exec cp -a {} dist ";"

.PHONY: debian
debian:
	echo python3 ./setup.py --command-packages=stdeb.command sdist_dsc --debian-version "$$(date '+%s')"  --with-python2=False --with-python3=True --suite xenial --maintainer "Grzegorz Gutowski <grzegorz.gutowski@uj.edu.pl>" bdist_deb 
	mkdir -p dist
	find Kolejka*/deb_dist -type f -name "*.deb" -exec cp -a {} dist ";"
	find Kolejka*/deb_dist -type f -name "*.dsc" -exec cp -a {} dist ";"
	find Kolejka*/deb_dist -type f -name "*.orig.tar.gz" -exec cp -a {} dist ";"
	find Kolejka*/deb_dist -type f -name "*.debian.tar.xz" -exec cp -a {} dist ";"
	find Kolejka*/deb_dist -type f -name "*_source.changes" -exec cp -a {} dist ";"
	find dist -type f -name "*_source.changes" -exec debsign --no-conf "-mGrzegorz Gutowski <grzegorz.gutowski@uj.edu.pl>" --re-sign -S {} ";"

launchpad: debian
	find dist -type f -name "*_source.changes" -exec debsign --no-conf "-mGrzegorz Gutowski <grzegorz.gutowski@uj.edu.pl>" --re-sign -S {} ";"
	find dist -type f -name "*_source.changes" -exec dput ppa:kolejka/kolejka {} ";"

.PHONY: collect
collect:

.PHONY: clean
clean:
	rm -rf dist
	rm -rf Kolejka*/deb_dist
	rm -rf Kolejka*/dist
	rm -rf Kolejka*/build
	rm -rf Kolejka*/.eggs
	rm -rf Kolejka*/__pycache__
	rm -rf Kolejka*/Kolejka*.egg-info
	rm -rf Kolejka*/Kolejka*.tar.gz

