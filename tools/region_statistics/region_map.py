#!/usr/bin/python3

import argparse
import xml.etree.ElementTree as ET

# Constants
MB = 1024 * 1024
SEGMENT_SIZE = 2 * MB
BAR_HEIGHT = 800  # Height of each vertical bar
BAR_WIDTH = 40    # Width of each vertical bar
SPACE_BETWEEN_BARS = 10  # Space between each bar
TEXT_OFFSET = 5
BAR_Y_OFFSET = 60

# Function to parse the input file
def parse_input_file(file_path):
    functions = []
    with open(file_path, 'r') as file:
        for line in file:
            # Skip empty lines or comments
            if not line.strip() or line.startswith('#'):
                continue
            # Split the line into address, size, and name
            parts = line.split()
            if len(parts) < 3:
                continue  # Skip malformed lines
            address = int(parts[0], 16)  # Convert hex address to integer
            size = int(parts[1], 16)   # Handle hex or decimal size
            name = ' '.join(parts[2:])  # Join the remaining parts as the function name
            functions.append((address, size, name))
    return functions

# Function to convert address to segment index
def address_to_segment(address):
    return address // SEGMENT_SIZE

# Function to calculate the occupancy of each segment
def calculate_occupancy(segments):
    occupancy = {}
    for segment_index, funcs in segments.items():
        total_size = sum(size for _, size, _ in funcs)
        occupancy[segment_index] = total_size / SEGMENT_SIZE
    return occupancy

# Function to draw the SVG
def draw_svg(functions, output_svg_path):
    # Group functions by segment
    segments = {}
    for start, size, name in functions:
        while size > 0:
            segment_index = address_to_segment(start)
            segment_start = segment_index * SEGMENT_SIZE
            segment_end = segment_start + SEGMENT_SIZE
            if start + size > segment_end:
                part_size = segment_end - start
            else:
                part_size = size

            if segment_index not in segments:
                segments[segment_index] = []
            segments[segment_index].append((start, part_size, name))

            start += part_size
            size -= part_size

    # Calculate occupancy ratios
    occupancy = calculate_occupancy(segments)

    # Calculate total SVG width
    num_segments = len(segments)
    svg_width = max(num_segments * (BAR_WIDTH + SPACE_BETWEEN_BARS), 240)
    svg_height = BAR_HEIGHT + 220  # Extra space for labels at the bottom

    # Create SVG root element
    svg = ET.Element('svg', width=str(svg_width), height=str(svg_height), xmlns="http://www.w3.org/2000/svg")

    # Sort segments by their start address (segment index)
    sorted_segments = sorted(segments.items())

    # Draw each segment
    for i, (segment_index, funcs) in enumerate(sorted_segments):
        x = i * (BAR_WIDTH + SPACE_BETWEEN_BARS)
        # Draw segment background
        ET.SubElement(svg, 'rect', x=str(x), y=str(BAR_Y_OFFSET), width=str(BAR_WIDTH), height=str(BAR_HEIGHT), fill='lightgray')
        
        # Draw functions within the segment
        for start, size, name in funcs:
            y = BAR_HEIGHT - ((start % SEGMENT_SIZE) / SEGMENT_SIZE) * BAR_HEIGHT + BAR_Y_OFFSET    
            height = (size / SEGMENT_SIZE) * BAR_HEIGHT
            # Draw function block
            rect = ET.SubElement(svg, 'rect', x=str(x), y=str(y - height), width=str(BAR_WIDTH), height=str(height), fill='blue')
            # Add tooltip with function details
            title = ET.SubElement(rect, 'title')
            title.text = f"Name: {name}\nAddress: 0x{start:08x}\nSize: {size} bytes"

        # Draw segment label (hex address) at the bottom, vertically aligned
        segment_start_address = segment_index * SEGMENT_SIZE
        segment_label = f"0x{segment_start_address:08x}"
        text = ET.SubElement(svg, 'text', x=str(x + BAR_WIDTH / 2 + 5), y=str(BAR_HEIGHT + BAR_Y_OFFSET + 110), fill='black', 
                             font_size="16", text_anchor="middle", transform=f"rotate(-90, {x + BAR_WIDTH / 2 + 5}, {BAR_HEIGHT + BAR_Y_OFFSET + 110})")
        text.text = segment_label

        # Draw occupancy ratio on top of each segment
        occupancy_ratio = occupancy.get(segment_index, 0)
        occupancy_text = f"{occupancy_ratio:.1%}"
        ET.SubElement(svg, 'text', x=str(x), y=str(BAR_Y_OFFSET - 2), fill='black', font_size="10", text_anchor="middle").text = occupancy_text

    # Add chart title at the top center.
    title = ET.SubElement(svg, 'text', x="0", y="20", fill="black", font_size="10", text_anchor="middle")
    title.text = "Code Distribution in 2MB Regions"

    # Add chart title at the top center.
    note = ET.SubElement(svg, 'text', x="0", y=str(BAR_HEIGHT + BAR_Y_OFFSET + 140), fill="black", font_size="10", text_anchor="middle")
    note.text = "Note: you can see function information by hovering pointer over the blue blocks."
    note1 = ET.SubElement(svg, 'text', x="37", y=str(BAR_HEIGHT + BAR_Y_OFFSET + 160), fill="black", font_size="10", text_anchor="middle")
    note1.text = "The blue blocks (size) only contains main code and stub code of each function"


    # Save SVG to file
    tree = ET.ElementTree(svg)
    tree.write(output_svg_path, encoding='utf-8', xml_declaration=True)

# Main execution
if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Generate an SVG memory map from a file.")
    parser.add_argument("input_file", help="Path to the input file containing memory mapping data.")
    parser.add_argument("output_file", help="Path to the output SVG file.")
    args = parser.parse_args()

    # Parse the input file
    functions = parse_input_file(args.input_file)

    # Draw the SVG
    draw_svg(functions, args.output_file)



