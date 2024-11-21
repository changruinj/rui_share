#!/usr/bin/python3

import mmap
import struct
import argparse
import sys
import os

# Define the structure
class AddressBuffers:
    def __init__(self, buffer_size):
        self.mitigation_start = 0
        self.clean_interval = 0
        self.valid_size1 = 0
        self.valid_size2 = 0
        self.active_buffer = 0
        self.pad = 0
        self.buffer1 = [0] * buffer_size
        self.buffer2 = [0] * buffer_size

# Constants
BUFFER_SIZE = 1048576 #1MB
MAP_FILE_NAME = "/dev/mitigation"
# Create an instance of AddressBuffers
address_buffers = AddressBuffers(BUFFER_SIZE)
total_mem_size = 24 + 2*BUFFER_SIZE


parser = argparse.ArgumentParser(description="Process some integers.")
parser.add_argument('-i', '--interval', type=int, help='Interval for mitigation in micro second')
parser.add_argument('-s', '--switch', type=str, choices=['on', 'off'], help='Switch on or off')
parser.add_argument('-d', '--dump', action='store_true', help='Dump code addresses')

args = parser.parse_args()

if len(sys.argv) == 1:
    parser.print_help(sys.stderr)
    sys.exit(1)

# Custom validation to ensure -s is not given together with both -i and -d
if args.switch is not None and (args.interval is not None or args.dump):
    print("Error: -s cannot be given together with either -i and -d.")
    sys.exit(1)

# Check if the file exists
if not os.path.exists(MAP_FILE_NAME):
    # if it doesn't exist
    print("device not found: {0}".format(MAP_FILE_NAME))
    sys.exit(1)

#print("total_mem_size {0}".format(total_mem_size))

with open('/dev/mitigation', 'r+b', buffering=0) as f:
    # Memory-map the file
    mm = mmap.mmap(f.fileno(), total_mem_size, access=mmap.ACCESS_WRITE)

    if args.switch == 'on':
        print("Switch is ON")
        # Perform actions for the 'on' state
        address_buffers.mitigation_start = 1
        # Write valid_size1, valid_size2, active_buffer
        mm.seek(0)
        mm.write(struct.pack('I', address_buffers.mitigation_start))
        sys.exit(0)
    elif args.switch == 'off':
        print("Switch is OFF")
        address_buffers.mitigation_start = 0
        # Perform actions for the 'off' state
        mm.seek(0)
        mm.write(struct.pack('I', address_buffers.mitigation_start))
        sys.exit(0)
    else:
        pass
    
    if args.interval is not None:
        address_buffers.clean_interval = args.interval
        mm.seek(struct.calcsize('I'))
        # Write the updated structure back to the file
        mm.write(struct.pack('I', address_buffers.clean_interval))
        print("Interval updated to {0}".format(address_buffers.clean_interval))
    
    
    if args.dump:
        # Read the content of ins-uniq.csv and fill buffer1
        with open('ins-uniq-kernel.csv', 'r') as ff:
            lines = ff.readlines()
            for i, line in enumerate(lines):
                if i < BUFFER_SIZE:
                    address_buffers.buffer1[i] = int(line.strip(), 16)
                    address_buffers.valid_size1 += 1
        
        # Create a binary file and write the structure to it
        # Write valid_size1, valid_size2, active_buffer
        mm.seek(struct.calcsize('II'))
        mm.write(struct.pack('I', address_buffers.valid_size1))
        mm.write(struct.pack('I', address_buffers.valid_size2))
        mm.write(struct.pack('I', address_buffers.active_buffer))
        mm.write(struct.pack('I', address_buffers.pad))
        
        # Write buffer1 and buffer2
        for i in range(address_buffers.valid_size1):
            value = address_buffers.buffer1[i]
            mm.write(struct.pack('Q', value))
        for i in range(address_buffers.valid_size2):
            value = address_buffers.buffer2[i]
            mm.write(struct.pack('Q', value))
    
        print("Memory map communication file created successfully.")

