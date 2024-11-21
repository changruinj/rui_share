ccflags-y := -O
obj-m := mitigation-module.o

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(shell pwd) modules

modules_install:
	make -C /lib/modules/$(shell uname -r)/build M=$(shell pwd) modules_install

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(shell pwd) clean
