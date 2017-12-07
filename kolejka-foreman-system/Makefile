.PHONY: squash
all : foreman.squashfs foreman.vmlinuz

.PHONY: build
build :
	docker build --tag kolejka.matinf.uj.edu.pl/kolejka:foreman .

foreman.squashfs : build
	./docker_squash kolejka.matinf.uj.edu.pl/kolejka:foreman foreman.squashfs

foreman.vmlinuz : foreman.squashfs
	./squash_extract_vmlinuz foreman.squashfs foreman.vmlinuz foreman.initrd

deploy :
	cp -a foreman.squashfs /srv/nfs/kolejka/foreman/casper/filesystem.squashfs
	cp -a foreman.vmlinuz /srv/tftp/configs/kolejka/foreman/vmlinuz
	cp -a foreman.initrd /srv/tftp/configs/kolejka/foreman/initrd
