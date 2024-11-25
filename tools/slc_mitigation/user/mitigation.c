#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <stdarg.h>

#define SIZE_1M 0x100000
#define BUFFER_SIZE (1*SIZE_1M)      //buffer size, may need change according to your program size. 
#define DEFAULT_CLEAN_INTERVAL 1000          //in micro seconds. may need tunning
#define MAP_FILE_NAME "/tmp/addr_buffer"
#define LOG_FILE "/tmp/mitigation.log"

typedef struct {
    uint32_t mitigation_start;
    uint32_t clean_interval;
    uint32_t valid_size1;
    uint32_t valid_size2;
    uint32_t active_buffer;    
    uint32_t pad;    
    uint64_t buffer1[BUFFER_SIZE];
    uint64_t buffer2[BUFFER_SIZE];
} AddressBuffers;

// Function to log a formatted message to the log file
void mitigate_log_message(int log_fd, const char *format, ...) {
    // Get the current timestamp
    char timestamp[20];
    time_t now = time(NULL);
    struct tm *t = localtime(&now);
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", t);

    // Write the timestamp to the log file
    dprintf(log_fd, "[%s] %u", timestamp, (unsigned)getpid());

    // Write the formatted message to the log file
    va_list args;
    va_start(args, format);
    vdprintf(log_fd, format, args);
    va_end(args);

    // Write a newline character to the log file
    dprintf(log_fd, "\n");
}

static void* mitigation_thread(void* args) 
{
    char addr_file[256];
    uint32_t pid = (unsigned)getpid();

    snprintf(addr_file, 256, MAP_FILE_NAME".%u", pid);

    int log_fd = open(LOG_FILE, O_RDWR | O_CREAT | O_APPEND, 0644);
    if (log_fd == -1) {
        perror("Failed to open log file");
        return NULL;
    }

    mitigate_log_message(log_fd, "\n\n\n");
    mitigate_log_message(log_fd, "=====================================\n");
    mitigate_log_message(log_fd, "=    mitigation_thread started      =\n");
    mitigate_log_message(log_fd, "=====================================\n");

    // Check if the file exists
    if (access(addr_file, F_OK) != -1) {
        // File exists, attempt to delete it
        if (remove(addr_file) == 0) {
            mitigate_log_message(log_fd, "The file %s was deleted successfully.\n", addr_file);
        } else {
            perror("Error deleting the file");
        }
    }

    int fd = open(addr_file, O_CREAT | O_RDWR, 0666);
    if (fd == -1) {
        perror("open");
        return NULL;
    }

    // Set the file size to 20MB
    if (ftruncate(fd, sizeof(AddressBuffers)) == -1) {
        perror("Error setting file size");
        close(fd);
        return NULL;
    }

    struct stat sb;
    if (fstat(fd, &sb) == -1) {
        perror("fstat");
        close(fd);
        return NULL;
    }

    AddressBuffers *addr_buffer = (AddressBuffers *)mmap(NULL, sb.st_size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (addr_buffer == MAP_FAILED) {
        perror("mmap");
        close(fd);
        return NULL;
    }


    uint64_t * buffer = addr_buffer->buffer1;
    uint64_t size = 0; 
    uint32_t clean_interval = DEFAULT_CLEAN_INTERVAL;

    uint32_t count=0;

    while (1) 
    {
	if (!addr_buffer->mitigation_start)
	{
            //mitigate_log_message(log_fd, "=====NOT started=======\n");
            sleep(1);
	}
	else
	{
            //mitigate_log_message(log_fd, "=====started=======\n");
            if (addr_buffer->clean_interval != 0)
            {
                clean_interval = addr_buffer->clean_interval;
            }

            size = addr_buffer->valid_size1;
            asm volatile("dsb ish" : : : "memory");
    
            for (int i = 0; i < size; ++i) 
            {
                asm volatile("dc civac, %0" : : "r" (buffer[i]) : "memory");
                //mitigate_log_message(log_fd, "%lx\n",buffer[i]);
            }
    
            asm volatile("dsb ish" : : : "memory");
            asm volatile("isb" : : : "memory");
    
       	    usleep(clean_interval);
            if (count++ == 10000)
            {
                count = 0;
                mitigate_log_message(log_fd, "=====finished 10000 round  sleep %d us=======\n", clean_interval);
            }
	}
    }

    munmap(addr_buffer, sizeof(AddressBuffers));
    close(fd);
    close(log_fd);
    return 0;
}

static void __attribute__((constructor)) mitigate() {
    pthread_t t;
    pthread_create(&t, NULL, mitigation_thread, NULL);
    pthread_detach(t);
}
