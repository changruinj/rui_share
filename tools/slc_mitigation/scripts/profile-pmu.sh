#!/bin/bash

# Function to check if a string is a number
is_number() {
    if [[ $1 =~ ^[0-9]+$ ]]; then
        return 0
    else
        return 1
    fi
}

if [ $# -eq 0 ]; then
    echo "Usage: $0 pid1 pid2 ..."
    exit 1
fi

if [ "$1" == "-h" ]; then
    echo "Usage: $0 pid1 pid2 ..."
    exit 1
fi

# Iterate over all input parameters
for pid in "$@"; do
    if is_number "$pid"; then

	rm -f perf.$pid.script
	rm -f ins.$pid.csv
	rm -f ins-kernel.$pid.csv
	rm -f ins-cacheline.$pid.csv
	rm -f ins-kernel-cacheline.$pid.csv
	rm -f ins-uniq.$pid.csv
	rm -f ins-uniq-kernel.csv

	echo "profiling $pid"
	perf record -F 20000 -p $pid -- sleep 3
	
	perf script > perf.$pid.script
	
	awk '!/ fff[a-f0-9]{13} /' perf.$pid.script | awk '{for(i=1;i<NF;i++) if($i ~ /^cycles(:P)?:$/) print $(i+1)}' > ins.$pid.csv
	awk '/ fff[a-f0-9]{13} /' perf.$pid.script | awk '{for(i=1;i<NF;i++) if($i ~ /^cycles(:P)?:$/) print $(i+1)}' > ins-kernel.$pid.csv
	
	# Do mitigation for every sampled PC
	#sort ins.$pid.csv | uniq  > ins-uniq.$pid.csv
	#sort ins-kernel.$pid.csv | uniq  > ins-uniq-kernel.csv	

        # Do mitigation in cache line granularity
        while read -r line; do printf "%x\n" $(( (16#$line >> 6) << 6 )); done < ./ins.$pid.csv > ins-cacheline.$pid.csv
        while read -r line; do printf "%x\n" $(( (16#$line >> 6) << 6 )); done < ./ins-kernel.$pid.csv > ins-kernel-cacheline.$pid.csv

        sort ins-cacheline.$pid.csv | uniq  > ins-uniq.$pid.csv
        sort ins-kernel-cacheline.$pid.csv | uniq  > ins-uniq-kernel.csv

	./mitigate-user.py -d -p $pid

    else
        echo "Error: '$pid' is not a number."
        exit 1
    fi
done

./mitigate-kernel.py -d
