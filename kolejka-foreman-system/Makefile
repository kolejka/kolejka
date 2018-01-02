.PHONY: all
all : clean build kolejka-foreman.squashfs kolejka-foreman.vmlinuz

.PHONY: clean
clean :
	rm -rf kolejka-foreman.squashfs kolejka-foreman.vmlinuz kolejka-foreman.initrd

.PHONY: build
build :
	docker build --no-cache --tag kolejka.matinf.uj.edu.pl/kolejka:foreman .
	docker push kolejka.matinf.uj.edu.pl/kolejka:foreman

kolejka-foreman.squashfs :
	docker pull kolejka.matinf.uj.edu.pl/kolejka:foreman
	./docker_squash kolejka.matinf.uj.edu.pl/kolejka:foreman kolejka-foreman.squashfs

kolejka-foreman.vmlinuz : kolejka-foreman.squashfs
	./squash_extract_vmlinuz kolejka-foreman.squashfs kolejka-foreman.vmlinuz kolejka-foreman.initrd

.PHONY: deploy
deploy :
	cp -a kolejka-foreman.squashfs /srv/nfs/kolejka/foreman/casper/filesystem.squashfs
	cp -a kolejka-foreman.vmlinuz /srv/tftp/configs/kolejka/foreman/vmlinuz
	cp -a kolejka-foreman.initrd /srv/tftp/configs/kolejka/foreman/initrd
	/root/bin/checker_restart 16
