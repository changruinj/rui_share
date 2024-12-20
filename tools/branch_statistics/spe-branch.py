#!/bin/python3

import csv

# Function to calculate indirect branch ratio
def indirect_branch_ratio(data):
    total_branches = len(data)
    indirect_branches = sum(1 for row in data if row[5].lower() == 'true')
    return indirect_branches / total_branches

# Function to calculate branch target address ratio that are more than 2MB away from current branch instruction address (PC)
def branch_target_ratio(data):
    total_branches = len(data)
    far_branches = 0
    for row in data:
        if abs(int(row[9], 16) - int(row[2], 16)) > (1024 * 1024 * 2):
            far_branches += 1
            #print("Far targets:")
            #print(row)
    return far_branches / total_branches

# Function to check how many cases that there are more than 4 branch operations and more than 3 branches
# where each row of record has a PC, and we need to figure out if in any 4 branch instructions' PC are in 32 byte range
def check_branch_operations(data):
    # Extract and sort unique PCs
    pcs = sorted(set(int(row[2], 16) for row in data))
    
    count = 0
    occurrences = []
    i = 0
    while i < len(pcs) -3:
        if pcs[i + 3] - pcs[i] <= 32:
            count += 1
            occurrences.append(pcs[i:i+4])
            i += 4
        else:
            i += 1
    return count, occurrences, len(pcs)

# Function to calculate ratio of branch target addresses that are not 32 byte aligned
def branch_not_aligned_ratio(data):
    total_branches = len(data)
    not_aligned_branches = 0
    for row in data:
        if int(row[9], 16) % 32 != 0:
            not_aligned_branches += 1
            #print("Not aligned targets:")
            #print(row)
    return not_aligned_branches / total_branches

# Read the CSV file
with open('spe-br.csv', mode='r') as file:
    csv_reader = csv.reader(file)
    header = next(csv_reader)  # Skip the header
    data = list(csv_reader)

# Calculate the ratios and counts
indirect_ratio = indirect_branch_ratio(data)
branch_target_ratio = branch_target_ratio(data)
branch_operations_count, occurrences, pcs = check_branch_operations(data)
not_aligned_ratio = branch_not_aligned_ratio(data)

print(f"Indirect Branch Ratio:                               {(indirect_ratio*100):.2f}%")
print(f"Branch Target Address More Than 2MB Away Ratio:      {(branch_target_ratio*100):.2f}%")
print(f"Branch Target Address Not Aligned to 32 Bytes Ratio: {(not_aligned_ratio*100):.2f}%")
print(f"More Than 4 Branch Operations in 32 Bytes:           {branch_operations_count}")
print(f"Total Unique Branch Instruction count:               %d" % pcs)
print(f"Total Branch Operation count:                        %d" % len(data))

# Save the PCs to another CSV file
with open('pcs_occurrences.csv', mode='w', newline='') as file:
    csv_writer = csv.writer(file)
    csv_writer.writerow(["PC1", "PC2", "PC3", "PC4"])
    for occurrence in occurrences:
        csv_writer.writerow([hex(pc) for pc in occurrence])

print("The 4 branch in 32 bytes samples saved to pcs_occurrences.csv")

