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

        rm -f spe-$pid-ldst.csv
        rm -f spe-$pid-br.csv
        rm -f spe-$pid-other.csv
        rm -f ins.$pid.csv
        rm -f ins-kernel.$pid.csv
        rm -f ins-cacheline.$pid.csv
        rm -f ins-kernel-cacheline.$pid.csv
        rm -f ins-uniq.$pid.csv
        rm -f ins-uniq-kernel.csv

        echo "profiling $pid"
        #perf record --no-switch-events  -e 'arm_spe_0/jitter=1/' -c 10240 -N  -p $pid -- sleep 1
        perf record --no-switch-events  -e 'arm_spe_0/jitter=1/' -c 20480 -N  -p $pid -- sleep 1
        
        spe-parser -s -t csv -p spe-$pid ./perf.data
        
        awk -F, '$4 == "0"' spe-$pid-ldst.csv | cut -f3 -d',' | sort | uniq >> ins.$pid.csv
        awk -F, '$4 == "0"' spe-$pid-br.csv | cut -f3 -d',' | sort | uniq >> ins.$pid.csv
        awk -F, '$4 == "0"' spe-$pid-other.csv | cut -f3 -d',' | sort | uniq >> ins.$pid.csv
        
        awk -F, '$4 == "2"' spe-$pid-ldst.csv | cut -f3 -d',' | sort | uniq >> ins-kernel.$pid.csv
        awk -F, '$4 == "2"' spe-$pid-br.csv | cut -f3 -d',' | sort | uniq >> ins-kernel.$pid.csv
        awk -F, '$4 == "2"' spe-$pid-other.csv | cut -f3 -d',' | sort | uniq >> ins-kernel.$pid.csv
        
        # Do mitigation for every sampled PC
        #sort ins.$pid.csv | uniq  > ins-uniq.$pid.csv
        #sort ins-kernel.$pid.csv | uniq  > ins-uniq-kernel.csv

        # Do mitigation in cache line granularity
	while read -r line; do printf "%x\n" $(( ($line >> 6) << 6 )); done < ./ins.$pid.csv > ins-cacheline.$pid.csv
        while read -r line; do printf "%x\n" $(( ($line >> 6) << 6 )); done < ./ins-kernel.$pid.csv > ins-kernel-cacheline.$pid.csv

        sort ins-cacheline.$pid.csv | uniq  > ins-uniq.$pid.csv
        sort ins-kernel-cacheline.$pid.csv | uniq  > ins-uniq-kernel.csv

        ./mitigate-user.py -d -p $pid

    else
        echo "Error: '$pid' is not a number."
        exit 1
    fi
done

./mitigate-kernel.py -d

