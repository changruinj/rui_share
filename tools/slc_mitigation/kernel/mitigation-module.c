#include <linux/version.h>
#include <linux/module.h> 
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/fs.h>
#include <linux/mm.h>
#include <linux/slab.h>
#include <linux/uaccess.h>
#include <linux/sysfs.h> 
#include <linux/kobject.h>
#include <linux/device.h>
#include <linux/delay.h>
#include <linux/kthread.h>

#define SIZE_1M 0x100000
#define DEFAULT_CLEAN_INTERVAL 1000          //in micro seconds. may need tunning

typedef struct {
    uint32_t mitigation_start;
    uint32_t clean_interval;
    uint32_t valid_size1;
    uint32_t valid_size2;
    uint32_t active_buffer;
    uint32_t pad;
    uint64_t buffer1;           // not the real buffer, just a indication   
    uint64_t buffer2;
} AddressBuffers;

static AddressBuffers *mitigation_data=NULL;

static size_t mem_size_mb = 1; // default 1 MB mem size for each buffer
static size_t mem_size = 0;
static int interval = 0;
static char switch_state[4] = "off";

static int major_number;
static struct class *my_class;
static struct device *my_device;
static struct task_struct *task;

module_param(mem_size_mb, ulong, S_IRUGO);
MODULE_PARM_DESC(mem_size_mb, "Buffer size to store addresses in MB");

static ssize_t interval_show(struct kobject *kobj, struct kobj_attribute *attr, char *buf) {
    return sprintf(buf, "%d\n", interval);
}

static ssize_t interval_store(struct kobject *kobj, struct kobj_attribute *attr, const char *buf, size_t count) {
    sscanf(buf, "%d", &interval);
    return count;
}

static ssize_t switch_show(struct kobject *kobj, struct kobj_attribute *attr, char *buf) {
    return sprintf(buf, "%s\n", switch_state);
}

static ssize_t switch_store(struct kobject *kobj, struct kobj_attribute *attr, const char *buf, size_t count) {
    if (strncmp(buf, "on", 2) == 0) {
        strcpy(switch_state, "on");
    } else if (strncmp(buf, "off", 3) == 0) {
        strcpy(switch_state, "off");
    }
    return count;
}

static struct kobj_attribute interval_attr = __ATTR(interval, 0664, interval_show, interval_store);
static struct kobj_attribute switch_attr = __ATTR(switch, 0664, switch_show, switch_store);

static struct attribute *attrs[] = {
    &interval_attr.attr,
    &switch_attr.attr,
    NULL,
};

static struct attribute_group attr_group = {
    .attrs = attrs,
};

static struct kobject *mitigate_kobj;

static int mitigate_open(struct inode *inode, struct file *file) {
    //pr_info("=====open get in\n");
    return 0;
}

static int mitigate_mmap(struct file *file, struct vm_area_struct *vma) {
    const unsigned long size = vma->vm_end - vma->vm_start;

    //pr_info("=====mmap get in\n");

    if (size > mem_size) {
        pr_err("Request size %lx bigger than allocated size %lx\n", size, mem_size);
        return -EINVAL;
    }
    vma->vm_page_prot = pgprot_noncached(vma->vm_page_prot);
    if (remap_pfn_range(vma, vma->vm_start, virt_to_phys(mitigation_data) >> PAGE_SHIFT, 
            size, vma->vm_page_prot)) {
        pr_err("Failed to map io memory\n");
        return -EAGAIN;
    }
    return 0;
}

static loff_t my_llseek(struct file *file, loff_t offset, int whence) {
    loff_t new_pos;

    switch (whence) {
        case SEEK_SET:
            new_pos = offset;
            break;
        case SEEK_CUR:
            new_pos = file->f_pos + offset;
            break;
        case SEEK_END:
            new_pos = mem_size + offset;
            break;
        default:
            return -EINVAL;
    }

    if (new_pos < 0 || new_pos > mem_size)
        return -EINVAL;

    file->f_pos = new_pos;
    return new_pos;
}

static const struct file_operations mitigate_fops = {
    .owner = THIS_MODULE,
    .open = mitigate_open,
    .mmap = mitigate_mmap,
    .llseek = my_llseek,
};


static int mitigation_thread(void* args) 
{
    pr_info("=====mitigation_thread started=======\n");

    uint64_t * buffer = &mitigation_data->buffer1;
    uint64_t size = 0; 
    uint32_t clean_interval = DEFAULT_CLEAN_INTERVAL;

    uint32_t count=0;
    uint64_t i = 0; 

    while (!kthread_should_stop()) {
        if (!mitigation_data->mitigation_start) {
            //pr_info("=====NOT started=======\n");
            msleep(1000);
        }
        else {
            //pr_info("=====started=======\n");
            if (mitigation_data->clean_interval != 0) {
                clean_interval = mitigation_data->clean_interval;
            }

            size = mitigation_data->valid_size1;
            asm volatile("dsb ish" : : : "memory");
   
            for (i = 0; i < size; ++i) {
                asm volatile("dc civac, %0" : : "r" (buffer[i]) : "memory");
	//	if (i/100==0)
	//	{pr_info("=====%lld %llx======\n", i, buffer[i]);}
            }
    
            asm volatile("dsb ish" : : : "memory");
            asm volatile("isb" : : : "memory");
    
            usleep_range(clean_interval, clean_interval+1);

            if (count++ == 10000) {
                count = 0;
                pr_info("=====finished 10000 round  sleep %d us=======\n", clean_interval);
            }
        }
    }

    return 0;
}


static int __init mitigate_init(void) {
    int retval;

    mem_size =  (sizeof(AddressBuffers) + 2*SIZE_1M * mem_size_mb) + PAGE_SIZE; // allocated 16 byte more than needed. 

    mitigation_data = kmalloc(mem_size, GFP_KERNEL);
    if (!mitigation_data) {
        pr_err("Failed to allocate memory\n");
        return -ENOMEM;
    }

    mitigate_kobj = kobject_create_and_add("mitigate_obj", kernel_kobj);
    if (!mitigate_kobj) {
        kfree(mitigation_data);
        return -ENOMEM;
    }

    retval = sysfs_create_group(mitigate_kobj, &attr_group);
    if (retval) {
        kobject_put(mitigate_kobj);
        kfree(mitigation_data);
        return retval;
    }

    major_number = register_chrdev(0, "mitigation", &mitigate_fops); 
    if (major_number < 0) {
        sysfs_remove_group(mitigate_kobj, &attr_group);
        kobject_put(mitigate_kobj);
        kfree(mitigation_data);
        return -EBUSY;
    }

#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 4, 0)
    my_class = class_create("mitigation");
#else
    my_class = class_create(THIS_MODULE, "mitigation");
#endif
    if (IS_ERR(my_class)) {
        unregister_chrdev(major_number, "mitigation");
        sysfs_remove_group(mitigate_kobj, &attr_group);
        kobject_put(mitigate_kobj);
        kfree(mitigation_data);
        return PTR_ERR(my_class);
    }

    my_device = device_create(my_class, NULL, MKDEV(major_number, 0), NULL, "mitigation");
    if (IS_ERR(my_device)) {
        class_destroy(my_class);
        unregister_chrdev(major_number, "mitigation");
        sysfs_remove_group(mitigate_kobj, &attr_group);
        kobject_put(mitigate_kobj);
        kfree(mitigation_data);
        return PTR_ERR(my_device);
    }

    task = kthread_create(mitigation_thread, NULL, "mitigation_thread");
    if (IS_ERR(task)) {
        pr_err("Failed to create thread\n");
        return PTR_ERR(task);
    }
    wake_up_process(task);

    pr_info("Driver loaded\n");
    return 0;
}

static void __exit mitigate_exit(void) {
    if (task) {
        kthread_stop(task);
        pr_info( "Thread stopped\n");
    }
    device_destroy(my_class, MKDEV(major_number, 0));
    class_destroy(my_class);
    unregister_chrdev(major_number, "mitigation");
    sysfs_remove_group(mitigate_kobj, &attr_group);
    kobject_put(mitigate_kobj);
    kfree(mitigation_data);
    pr_info("Driver unloaded\n");
}

module_init(mitigate_init);
module_exit(mitigate_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Rui Chang");
MODULE_DESCRIPTION("Mitigate SLC miss");
