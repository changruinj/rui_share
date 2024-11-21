CFLAGS += -O2 -g

all: mitigation.so

mitigation.so: mitigation.c
	$(CC) $(CFLAGS) -fPIC -shared $^ -lpthread -o mitigation.so

clean:
	rm -f mitigation.so 

