#!/usr/bin/env python3
"""
Gigamon 'show diag' Parser
Parses Gigamon diagnostic files to extract port inventory information.
"""

import re
import sys

def parse_gigamon_diag(file_path):
    """
    Parses a Gigamon 'show diag' file to extract port inventory.
    """
    
    # Dictionaries to store data
    # Key = Port ID (e.g., "1/1/x1")
    port_aliases = {}
    port_data = {}

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return

    # --- STEP 1: Parse Running Config for Full Aliases ---
    # We do this because the 'Port Params' table often truncates long aliases.
    # We look for lines like: port 1/1/x1 alias My_Long_Alias_Name
    
    in_running_config = False
    alias_pattern = re.compile(r'^\s*port\s+([0-9]+/[0-9]+/[a-z0-9]+)\s+alias\s+(.+)')
    
    for line in lines:
        if "Running Configuration" in line:
            in_running_config = True
        
        if in_running_config:
            match = alias_pattern.match(line)
            if match:
                port_id = match.group(1)
                alias = match.group(2).strip().replace('"', '') # Remove quotes if present
                port_aliases[port_id] = alias

    # --- STEP 2: Parse Port Parameters Table ---
    # This section contains Speed, Type, Status, and SFP info.
    # The table is transposed (columns are ports), so we parse blocks.

    current_ports = []
    
    # Regex to find the header row of a block (e.g., "Parameter  1/1/x1  1/1/x2")
    header_pattern = re.compile(r'^\s*Parameter\s+(1/\d+/\S+.*)')
    
    for line in lines:
        line = line.strip()
        
        # Detect Header Row
        match = header_pattern.match(line)
        if match:
            # Split by multiple spaces to get port IDs
            current_ports = re.split(r'\s{2,}', match.group(1))
            # Initialize these ports in our dictionary
            for p in current_ports:
                if p not in port_data:
                    port_data[p] = {
                        "Type": "N/A", 
                        "Admin": "N/A", 
                        "Speed": "N/A", 
                        "SFP": "N/A",
                        "Media": "N/A"
                    }
            continue

        # Skip separator lines
        if line.startswith("=") or not current_ports:
            continue

        # Extract Attributes based on row label
        # We split the line by 2+ spaces. Index 0 is label, 1..N are values
        parts = re.split(r'\s{2,}', line)
        
        if len(parts) < 2: 
            continue
            
        label = parts[0].replace(":", "").strip()
        values = parts[1:]

        # specific mappings
        if label == "Type":
            for i, val in enumerate(values):
                if i < len(current_ports):
                    port_data[current_ports[i]]["Type"] = val
        
        elif label == "Admin":
            for i, val in enumerate(values):
                if i < len(current_ports):
                    port_data[current_ports[i]]["Admin"] = val

        elif label == "Speed (Mbps)":
            for i, val in enumerate(values):
                if i < len(current_ports):
                    speed_val = val
                    # Format Speed
                    if val == "1000": speed_val = "1Gb"
                    elif val == "10000": speed_val = "10Gb"
                    elif val == "40000": speed_val = "40Gb"
                    elif val == "100000": speed_val = "100Gb"
                    port_data[current_ports[i]]["Speed"] = speed_val

        elif label == "SFP type":
            for i, val in enumerate(values):
                if i < len(current_ports):
                    sfp_val = val
                    port_data[current_ports[i]]["SFP"] = sfp_val
                    
                    # Determine Media Type Logic
                    media = "Unknown"
                    val_lower = val.lower()
                    
                    if "cu" in val_lower or "copper" in val_lower:
                        media = "Copper"
                    elif any(x in val_lower for x in ['sx', 'lx', 'sr', 'lr', 'er', 'zr']):
                        media = "Fiber"
                    elif "qsfp" in val_lower:
                        media = "Fiber (QSFP)"
                    elif val_lower in ["none", "n/a", "(unsupported)"]:
                        media = "No Module"
                    else:
                        media = val # Fallback
                        
                    port_data[current_ports[i]]["Media"] = media

    # --- STEP 3: Formatting Output ---
    
    print(f"{'Port':<10} {'Type':<12} {'Alias':<35} {'Status':<10} {'Speed':<8} {'Media':<15}")
    print("-" * 95)

    # Sort ports naturally (x1, x2, x10 instead of x1, x10, x2)
    def natural_keys(text):
        return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', text)]

    for port in sorted(port_data.keys(), key=natural_keys):
        data = port_data[port]
        
        # Merge the alias we found in config, or use "-"
        alias = port_aliases.get(port, "-")
        
        # Capitalize status
        status = data["Admin"].capitalize()
        
        # Clean up Type (remove extra info like (T))
        p_type = data["Type"].replace("(T)", "")

        print(f"{port:<10} {p_type:<12} {alias:<35} {status:<10} {data['Speed']:<8} {data['Media']:<15}")

    # --- Summary Counts ---
    print("\n--- Summary ---")
    enabled_count = sum(1 for p in port_data.values() if p["Admin"].lower() == "enabled")
    disabled_count = sum(1 for p in port_data.values() if p["Admin"].lower() == "disabled")
    
    print(f"Total Ports Found: {len(port_data)}")
    print(f"Enabled: {enabled_count}")
    print(f"Disabled: {disabled_count}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gigamon_parser.py <log_file>")
    else:
        parse_gigamon_diag(sys.argv[1])
