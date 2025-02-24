#!/usr/bin/python3

import os
import shutil
import sys
import re
import subprocess
import argparse
import logging
import matplotlib.pyplot as plt
import csv
import seaborn as sns
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Function to check if a file exists
def file_exists(file_path):
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        sys.exit(1)

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Process perf data using spe-parser.")
parser.add_argument("perf_data_file", help="Path to the perf.data file")
args = parser.parse_args()

filename = args.perf_data_file

# Validate input file
file_exists(filename)


# Remove existing files 
files_to_remove = [
    f"spe-{filename}-ldst.csv",
    f"spe-{filename}-br.csv",
    f"spe-{filename}-other.csv",
    f"ins.{filename}.csv",
    f"ins-kernel.{filename}.csv",
    f"ins-uniq.{filename}.csv",
    f"ins-uniq-kernel.{filename}.csv",
    f"ins-cacheline.{filename}.csv",
    f"ins-kernel-cacheline.{filename}.csv",
    f"ins-cacheline-uniq.{filename}.csv",
    f"ins-cacheline-uniq-kernel.{filename}.csv",
    f"ins-2mb-range-counts.{filename}.csv",
    f"ins-kernel-2mb-range-counts.{filename}.csv",
    f"ins-1k-touch-ratio.{filename}.csv",
    f"ins-kernel-1k-touch-ratio.{filename}.csv",
    f"ins-cacheline-touch-ratio.{filename}.csv",
    f"ins-kernel-cacheline-touch-ratio.{filename}.csv",
    f"ins-2mb-range-histogram.{filename}.png",
    f"ins-kernel-2mb-range-histogram.{filename}.png",
    f"ins-1k-touch-ratio-histogram.{filename}.png",
    f"ins-kernel-1k-touch-ratio-histogram.{filename}.png",
    f"ins-cacheline-touch-ratio-histogram.{filename}.png",
    f"ins-kernel-cacheline-touch-ratio-histogram.{filename}.png",
    f"br.{filename}.csv",
    f"br-kernel.{filename}.csv",
    f"br.{filename}.png",
    f"br-kernel.{filename}.png",
]

if os.path.exists(f"{filename}-output"):
    shutil.rmtree(f"{filename}-output")
    logging.info(f"Removed folder: {filename}-output")


# Run spe-parser
try:
    logging.info(f"Running spe-parser on {filename}")
    subprocess.run(["spe-parser", "-s", "-t", "csv", "-p", f"spe-{filename}", filename], check=True)
except subprocess.CalledProcessError as e:
    logging.error(f"Error running spe-parser: {e}")
    sys.exit(1)

# Process CSV files to extract instructions
def process_csv_pc(input_file, output_file, exception_level):
    unique_lines = set()  # Use a set to store unique lines
    try:
        with open(output_file, "a") as outfile:
            with open(input_file, "r") as infile:
                for line in infile:
                    if line.split(",")[3] == exception_level:
                        outfile.write(line.split(",")[2].strip() + "\n") 
        logging.info(f"Processed {input_file} -> {output_file}")
    except Exception as e:
        logging.error(f"Error processing {input_file}: {e}")

# Process user-space instructions
process_csv_pc(f"spe-{filename}-ldst.csv", f"ins.{filename}.csv", "0")
process_csv_pc(f"spe-{filename}-br.csv", f"ins.{filename}.csv", "0")
process_csv_pc(f"spe-{filename}-other.csv", f"ins.{filename}.csv", "0")

# Process kernel-space instructions
process_csv_pc(f"spe-{filename}-ldst.csv", f"ins-kernel.{filename}.csv", "2")
process_csv_pc(f"spe-{filename}-br.csv", f"ins-kernel.{filename}.csv", "2")
process_csv_pc(f"spe-{filename}-other.csv", f"ins-kernel.{filename}.csv", "2")

# Deduplicate PCs
def sort_and_deduplicate(input_file, output_file):
    try:
        with open(input_file, "r") as infile:
            lines = sorted(set(infile.readlines()))
        with open(output_file, "w") as outfile:
            outfile.writelines(lines)
        logging.info(f"Sorted and deduplicated {input_file} -> {output_file}")
    except Exception as e:
        logging.error(f"Error sorting and deduplicating {input_file}: {e}")

# Sort and deduplicate PCs
sort_and_deduplicate(f"ins.{filename}.csv", f"ins-uniq.{filename}.csv")
sort_and_deduplicate(f"ins-kernel.{filename}.csv", f"ins-uniq-kernel.{filename}.csv")

# Convert addresses to cacheline granularity
def convert_to_cacheline(input_file, output_file):
    try:
        with open(input_file, "r") as infile, open(output_file, "w") as outfile:
            for line in infile:
                address = int(line.strip(), 16)
                cacheline_address = (address >> 6) << 6
                outfile.write(f"{cacheline_address:x}\n")
        logging.info(f"Converted {input_file} -> {output_file}")
    except Exception as e:
        logging.error(f"Error converting {input_file}: {e}")

convert_to_cacheline(f"ins-uniq.{filename}.csv", f"ins-cacheline.{filename}.csv")
convert_to_cacheline(f"ins-uniq-kernel.{filename}.csv", f"ins-kernel-cacheline.{filename}.csv")

# Sort and deduplicate cacheline files
sort_and_deduplicate(f"ins-cacheline.{filename}.csv", f"ins-cacheline-uniq.{filename}.csv")
sort_and_deduplicate(f"ins-kernel-cacheline.{filename}.csv", f"ins-cacheline-uniq-kernel.{filename}.csv")

# Calculate 2MB range hit counts
def calculate_2mb_range_counts(input_file, output_file):
    """
    Calculate the occurrence count of PCs in each 2MB address range.
    
    Args:
        input_file (str): Path to the input CSV file containing addresses.
        output_file (str): Path to the output file to save the results.
    """
    range_counts = {}
    try:
        with open(input_file, "r") as infile:
            for line in infile:
                address = int(line.strip(), 16)
                range_start = (address // (2 * 1024 * 1024)) * (2 * 1024 * 1024)
                range_key = f"0x{range_start:x}"
                if range_key in range_counts:
                    range_counts[range_key] += 1
                else:
                    range_counts[range_key] = 1

        with open(output_file, "w") as outfile:
            for range_start, count in sorted(range_counts.items()):
                outfile.write(f"{range_start}: {count}\n")
        logging.info(f"Processed {input_file} -> {output_file}")
    except Exception as e:
        logging.error(f"Error processing {input_file}: {e}")

calculate_2mb_range_counts(f"ins.{filename}.csv", f"ins-2mb-range-counts.{filename}.csv")
calculate_2mb_range_counts(f"ins-kernel.{filename}.csv", f"ins-kernel-2mb-range-counts.{filename}.csv")

# Calculate address space touch ratio in 1K granularity for each 2MB range
def calculate_1k_touch_ratio(input_2mb_file, input_pc_file, output_file):
    """
    Calculate the ratio of touched 1K spaces vs. total 1K spaces in each 2MB range.
    
    Args:
        input_2mb_file (str): Path to the input CSV file containing 2MB range counts.
        input_pc_file (str): Path to the input file containing unique PC addresses.
        output_file (str): Path to the output file to save the results.
    """
    touched_1k_spaces = {}
    try:
        with open(input_2mb_file, "r") as infile:
            for line in infile:
                range_start, count = line.strip().split(": ")
                range_start = int(range_start, 16)
                touched_1k_spaces[range_start] = set()

        with open(input_pc_file, "r") as pc_file:
            for line in pc_file:
                pc_address = int(line.strip(), 16)
                range_start = (pc_address // (2 * 1024 * 1024)) * (2 * 1024 * 1024)
                if range_start in touched_1k_spaces:
                    chunk_offset = (pc_address - range_start) // 1024
                    touched_1k_spaces[range_start].add(chunk_offset)
        
        with open(output_file, "w") as outfile:
            for range_start, touched_chunks in touched_1k_spaces.items():
                total_1k_chunks = 2048
                touched_count = len(touched_chunks)
                ratio = touched_count / total_1k_chunks
                outfile.write(f"0x{range_start:x}: {ratio:.4f}\n")

        logging.info(f"Processed {input_pc_file} -> {output_file}")

    except Exception as e:
        logging.error(f"Error calculating 1K touch ratio for {input_pc_file}: {e}")

calculate_1k_touch_ratio(
    f"ins-2mb-range-counts.{filename}.csv", 
    f"ins.{filename}.csv", 
    f"ins-1k-touch-ratio.{filename}.csv"
)
calculate_1k_touch_ratio(
    f"ins-kernel-2mb-range-counts.{filename}.csv", 
    f"ins-kernel.{filename}.csv", 
    f"ins-kernel-1k-touch-ratio.{filename}.csv"
)

# Calculate address space touch ratio in cache line granularity for each 2MB range
def calculate_cacheline_touch_ratio(input_2mb_file, input_cacheline_file, output_file):
    """
    Calculate the ratio of touched cachelines vs. total cachelines in each 2MB range.
    
    Args:
        input_2mb_file (str): Path to the input CSV file containing 2MB range counts.
        input_cacheline_file (str): Path to the input file containing unique cache line addresses.
        output_file (str): Path to the output file to save the results.
    """
    touched_cachelines = {}
    try:
        with open(input_2mb_file, "r") as infile:
            for line in infile:
                range_start, count = line.strip().split(": ")
                range_start = int(range_start, 16)
                touched_cachelines[range_start] = set()

        with open(input_cacheline_file, "r") as cacheline_file:
            for line in cacheline_file:
                cacheline_address = int(line.strip(), 16)
                range_start = (cacheline_address // (2 * 1024 * 1024)) * (2 * 1024 * 1024)
                if range_start in touched_cachelines:
                    touched_cachelines[range_start].add(cacheline_address)
        
        with open(output_file, "w") as outfile:
            for range_start, touched_cachelines in touched_cachelines.items():
                total_cachelines = 32768
                touched_count = len(touched_cachelines)
                ratio = touched_count / total_cachelines
                outfile.write(f"0x{range_start:x}: {ratio:.4f}\n")

        logging.info(f"Processed {input_cacheline_file} -> {output_file}")

    except Exception as e:
        logging.error(f"Error calculating cacheline touch ratio for {input_cacheline_file}: {e}")

calculate_cacheline_touch_ratio(
    f"ins-2mb-range-counts.{filename}.csv", 
    f"ins-cacheline-uniq.{filename}.csv", 
    f"ins-cacheline-touch-ratio.{filename}.csv"
)
calculate_cacheline_touch_ratio(
    f"ins-kernel-2mb-range-counts.{filename}.csv", 
    f"ins-cacheline-uniq-kernel.{filename}.csv", 
    f"ins-kernel-cacheline-touch-ratio.{filename}.csv"
)

# Plot hitogram for 2MB range count files
def plot_occurrence_count_hitogram(input_file, title, output_image):
    """
    Plot a hitogram for the occurrence counts in a 2MB range file.
    
    Args:
        input_file (str): Path to the input CSV file containing 2MB range counts.
        title (str): Title for the hitogram.
        output_image (str): Path to save the hitogram image.
    """
    ranges = []
    counts = []

    try:
        # Read the input file
        with open(input_file, "r") as infile:
            for line in infile:
                range_start, count = line.strip().split(": ")
                ranges.append(range_start)
                counts.append(int(count))

        # Calculate figure size
        range_count = len(ranges)
        bar_width = 0.15  # Width of each bar
        
        fig_width = range_count * bar_width
        fig_height = fig_width / 2
        
        # Ensure minimum and maximum figure size
        fig_width = max(8, min(fig_width, 60))  # Minimum width: 10 inches, Maximum width: 50 inches
        fig_height = max(8, min(fig_height, 30))  # Minimum height: 8 inches, Maximum height: 40 inches
        
        # Create a larger figure
        plt.figure(figsize=(fig_width, fig_height))  # Increase the figure size (width, height)
        
        # Plot the hitogram
        bars = plt.bar(ranges, counts, color='blue', alpha=0.7)

        # Add labels and title
        plt.xlabel("2MB Range Start Address", fontsize=12)
        plt.ylabel("Occurrence Count", fontsize=12)
        plt.title(title, fontsize=14)

        # Rotate x-axis labels for better readability
        plt.xticks(rotation=90, fontsize=10)

        # Add grid lines for better readability
        plt.grid(axis='y', linestyle='--', alpha=0.7)

        # Add numbers (ratios) on top of each bar
        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2,  # X position (center of the bar)
                height + 1000,  # Y position (slightly above the bar)
                f"{height}",  # Text to display (ratio)
                ha='center',  # Horizontal alignment (center)
                va='bottom',  # Vertical alignment (bottom)
                fontsize=8,   # Font size
                color='black', # Text color
                rotation=90   # Rotate text vertically
            )
            
        # Adjust layout to prevent label overlap
        plt.tight_layout()

        # Save the hitogram as an image
        plt.savefig(output_image, dpi=300)  # Increase DPI for higher resolution
        logging.info(f"hitogram saved to {output_image}")

        # Optionally, display the hitogram
        # plt.show()

    except Exception as e:
        logging.error(f"Error plotting hitogram for {input_file}: {e}")
        
plot_occurrence_count_hitogram(
    f"ins-2mb-range-counts.{filename}.csv", 
    "User-Space 2MB Range Occurrence Counts", 
    f"ins-2mb-range-histogram.{filename}.png"
)
plot_occurrence_count_hitogram(
    f"ins-kernel-2mb-range-counts.{filename}.csv", 
    "Kernel-Space 2MB Range Occurrence Counts", 
    f"ins-kernel-2mb-range-histogram.{filename}.png"
)

# Plot histograms touch ratios
def plot_touch_ratio_histogram(input_file, title, output_image):
    """
    Plot a histogram for the address space touch ratios in each 2MB range.
    
    Args:
        input_file (str): Path to the input CSV file containing touch ratios in each 2MB range.
        title (str): Title for the histogram.
        output_image (str): Path to save the histogram image.
    """
    ranges = []
    ratios = []

    try:
        # Read the input file
        with open(input_file, "r") as infile:
            for line in infile:
                range_start, ratio = line.strip().split(": ")
                ranges.append(range_start)
                ratios.append(float(ratio))

        # Calculate figure size
        range_count = len(ranges)
        bar_width = 0.15  # Width of each bar
        
        fig_width = range_count * bar_width
        fig_height = fig_width / 2
        
        # Ensure minimum and maximum figure size
        fig_width = max(8, min(fig_width, 60))  # Minimum width: 10 inches, Maximum width: 50 inches
        fig_height = max(8, min(fig_height, 30))  # Minimum height: 8 inches, Maximum height: 40 inches
        
        # Create a larger figure
        plt.figure(figsize=(fig_width, fig_height))  # Increase the figure size (width, height)

        # Plot the histogram
        bars = plt.bar(ranges, ratios, color='blue', alpha=0.7)

        # Add labels and title
        plt.xlabel("2MB Range Start Address", fontsize=12)
        plt.ylabel("1K Granularity Touch Ratio", fontsize=12)
        plt.title(title, fontsize=14)

        # Rotate x-axis labels for better readability
        plt.xticks(rotation=90, fontsize=10)

        # Add grid lines for better readability
        plt.grid(axis='y', linestyle='--', alpha=0.7)

        # Add numbers (ratios) on top of each bar
        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2,  # X position (center of the bar)
                height + 0.002,  # Y position (slightly above the bar)
                f"{height:.2%}",  # Text to display (ratio)
                ha='center',  # Horizontal alignment (center)
                va='bottom',  # Vertical alignment (bottom)
                fontsize=8,   # Font size
                color='black', # Text color
                rotation=90   # Rotate text vertically
            )

        # Adjust layout to prevent label overlap
        plt.tight_layout()

        # Save the histogram as an image
        plt.savefig(output_image, dpi=300)  # Increase DPI for higher resolution
        logging.info(f"Histogram saved to {output_image}")

        # Optionally, display the histogram
        # plt.show()

    except Exception as e:
        logging.error(f"Error plotting histogram for {input_file}: {e}")

# Plot histograms for 1K granularity touch ratios
plot_touch_ratio_histogram(
    f"ins-1k-touch-ratio.{filename}.csv", 
    "User-Space 1K Granularity Touch Ratios for 2MB Ranges", 
    f"ins-1k-touch-ratio-histogram.{filename}.png"
)
plot_touch_ratio_histogram(
    f"ins-kernel-1k-touch-ratio.{filename}.csv", 
    "Kernel-Space 1K Granularity Touch Ratios for 2MB Ranges", 
    f"ins-kernel-1k-touch-ratio-histogram.{filename}.png"
)

# Plot histograms for cacheline granularity touch ratios
plot_touch_ratio_histogram(
    f"ins-cacheline-touch-ratio.{filename}.csv", 
    "User-Space Cacheline Granularity Touch Ratios for 2MB Ranges", 
    f"ins-cacheline-touch-ratio-histogram.{filename}.png"
)
plot_touch_ratio_histogram(
    f"ins-kernel-cacheline-touch-ratio.{filename}.csv", 
    "Kernel-Space Cacheline Granularity Touch Ratios for 2MB Ranges", 
    f"ins-kernel-cacheline-touch-ratio-histogram.{filename}.png"
) 

# Read the br.csv file and process the data
def process_br_csv(input_file, output_file, el=None):
    pc_br_tgt_counts = {}  # Dictionary to store counts of jumps between 2MB regions

    try:
        with open(input_file, "r") as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                # Filter out lines containing "NOT-TAKEN"
                if "NOT-TAKEN" not in row["event"]:
                    if el is None or row["el"] == el:
                            pc = row["pc"]
                            br_tgt = row["br_tgt"]

                            # Convert addresses to 2MB regions
                            pc_region = (int(pc, 16) // (2 * 1024 * 1024)) * (2 * 1024 * 1024)
                            br_tgt_region = (int(br_tgt, 16) // (2 * 1024 * 1024)) * (2 * 1024 * 1024)

                            # Update the count for this (pc_region, br_tgt_region) pair
                            key = (pc_region, br_tgt_region)
                            if key in pc_br_tgt_counts:
                                pc_br_tgt_counts[key] += 1
                            else:
                                pc_br_tgt_counts[key] = 1

        # Sort the data by pc_2mb_region
        sorted_counts = sorted(pc_br_tgt_counts.items(), key=lambda x: x[0][0])  # Sort by pc_region

        # Save the results to a CSV file
        with open(output_file, "w", newline="") as outfile:
            writer = csv.writer(outfile)
            writer.writerow(["pc_2mb_region", "br_tgt_2mb_region", "count"])
            for (pc_region, br_tgt_region), count in sorted_counts:
                writer.writerow([f"0x{pc_region:x}", f"0x{br_tgt_region:x}", count])

        logging.info(f"Processed {input_file} -> {output_file}")

        # Return the counts for heatmap generation
        return pc_br_tgt_counts

    except Exception as e:
        logging.error(f"Error processing {input_file}: {e}")
        return None


# Function to draw a heatmap
def plot_heatmap(pc_br_tgt_counts, output_image):
    try:
        # Extract unique 2MB regions for pc and br_tgt
        pc_regions = sorted(set(pc for pc, _ in pc_br_tgt_counts.keys()))
        br_tgt_regions = sorted(set(br_tgt for _, br_tgt in pc_br_tgt_counts.keys()))

        # Create a matrix to store counts
        heatmap_data = np.zeros((len(pc_regions), len(br_tgt_regions)), dtype=int)

        # Fill the matrix with counts
        for (pc_region, br_tgt_region), count in pc_br_tgt_counts.items():
            pc_index = pc_regions.index(pc_region)
            br_tgt_index = br_tgt_regions.index(br_tgt_region)
            heatmap_data[pc_index, br_tgt_index] = count

        # Dynamically adjust figure size based on the number of regions
        pc_count = len(pc_regions)
        br_tgt_count = len(br_tgt_regions)

        # Base size for each cell
        cell_width = 0.3  # Width of each cell in inches
        cell_height = 0.3  # Height of each cell in inches

        # Calculate figure size
        fig_width = br_tgt_count * cell_width
        fig_height = pc_count * cell_height

        # Ensure minimum and maximum figure size
        fig_width = max(8, min(fig_width, 50))  # Minimum width: 10 inches, Maximum width: 50 inches
        fig_height = max(8, min(fig_height, 50))  # Minimum height: 8 inches, Maximum height: 40 inches

        # Create the heatmap with dynamically adjusted figure size
        plt.figure(figsize=(fig_width, fig_height))
        sns.heatmap(
            heatmap_data,
            annot=True,
            fmt="d",
            cmap="YlOrRd",
            annot_kws={"size": 4},  # Adjust annotation font size
            xticklabels=[f"0x{region:x}" for region in br_tgt_regions],
            yticklabels=[f"0x{region:x}" for region in pc_regions],
        )
        plt.xlabel("Branch Target 2MB Region")
        plt.ylabel("PC 2MB Region")
        plt.title("Heatmap of Jumps Between 2MB Regions")
        plt.tight_layout()

        # Save the heatmap as an image
        plt.savefig(output_image, dpi=300)
        logging.info(f"Heatmap saved to {output_image}")

        # Optionally, display the heatmap
        # plt.show()

    except Exception as e:
        logging.error(f"Error drawing heatmap: {e}")


pc_br_tgt_counts_user = process_br_csv(f"spe-{filename}-br.csv", f"br.{filename}.csv", "0")
plot_heatmap(pc_br_tgt_counts_user, f"br.{filename}.png")

pc_br_tgt_counts_kernel = process_br_csv(f"spe-{filename}-br.csv", f"br-kernel.{filename}.csv", "2")
plot_heatmap(pc_br_tgt_counts_kernel, f"br-kernel.{filename}.png")


# Create the output folder if it doesn't exist
if not os.path.exists(f"{filename}-output"):
    os.makedirs(f"{filename}-output")

# Move the files to the folder
for file in files_to_remove:
    if os.path.exists(file):
        shutil.move(file, os.path.join(f"{filename}-output", file))
        #logging.info(f"Moved {file} to folder {filename}")


logging.info("Processing completed successfully.")
