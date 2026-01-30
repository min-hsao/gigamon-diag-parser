#!/usr/bin/env python3
"""
Gigamon 'show diag' Parser
Parses Gigamon diagnostic files to extract port inventory information.
"""

import argparse
import re
import sys

def parse_gigamon_diag(file_path, output_format='table', show_summary=True):
    """
    Parses a Gigamon 'show diag' file to extract port inventory.
    
    Args:
        file_path: Path to the show diag file
        output_format: 'table', 'csv', or 'json'
        show_summary: Whether to print summary counts
    """
    
    # Dictionaries to store data
    port_aliases = {}
    port_data = {}

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.", file=sys.stderr)
        sys.exit(1)

    # --- STEP 1: Parse Running Config for Full Aliases ---
    in_running_config = False
    alias_pattern = re.compile(r'^\s*port\s+([0-9]+/[0-9]+/[a-z0-9]+)\s+alias\s+(.+)')
    
    for line in lines:
        if "Running Configuration" in line:
            in_running_config = True
        
        if in_running_config:
            match = alias_pattern.match(line)
            if match:
                port_id = match.group(1)
                alias = match.group(2).strip().replace('"', '')
                port_aliases[port_id] = alias

    # --- STEP 2: Parse Port Parameters Table ---
    current_ports = []
    header_pattern = re.compile(r'^\s*Parameter\s+(1/\d+/\S+.*)')
    
    for line in lines:
        line = line.strip()
        
        match = header_pattern.match(line)
        if match:
            current_ports = re.split(r'\s{2,}', match.group(1))
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

        if line.startswith("=") or not current_ports:
            continue

        parts = re.split(r'\s{2,}', line)
        
        if len(parts) < 2: 
            continue
            
        label = parts[0].replace(":", "").strip()
        values = parts[1:]

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
                        media = val
                        
                    port_data[current_ports[i]]["Media"] = media

    # --- STEP 3: Output ---
    
    def natural_keys(text):
        return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', text)]

    sorted_ports = sorted(port_data.keys(), key=natural_keys)
    
    if output_format == 'json':
        import json
        output = []
        for port in sorted_ports:
            data = port_data[port]
            output.append({
                "port": port,
                "type": data["Type"].replace("(T)", ""),
                "alias": port_aliases.get(port, ""),
                "status": data["Admin"].capitalize(),
                "speed": data["Speed"],
                "media": data["Media"]
            })
        print(json.dumps(output, indent=2))
        
    elif output_format == 'csv':
        print("Port,Type,Alias,Status,Speed,Media")
        for port in sorted_ports:
            data = port_data[port]
            alias = port_aliases.get(port, "").replace(",", ";")
            p_type = data["Type"].replace("(T)", "")
            status = data["Admin"].capitalize()
            print(f'{port},{p_type},"{alias}",{status},{data["Speed"]},{data["Media"]}')
            
    else:  # table format
        print(f"{'Port':<10} {'Type':<12} {'Alias':<35} {'Status':<10} {'Speed':<8} {'Media':<15}")
        print("-" * 95)

        for port in sorted_ports:
            data = port_data[port]
            alias = port_aliases.get(port, "-")
            status = data["Admin"].capitalize()
            p_type = data["Type"].replace("(T)", "")
            print(f"{port:<10} {p_type:<12} {alias:<35} {status:<10} {data['Speed']:<8} {data['Media']:<15}")

    # --- Summary ---
    if show_summary and output_format == 'table':
        print("\n--- Summary ---")
        enabled_count = sum(1 for p in port_data.values() if p["Admin"].lower() == "enabled")
        disabled_count = sum(1 for p in port_data.values() if p["Admin"].lower() == "disabled")
        
        print(f"Total Ports Found: {len(port_data)}")
        print(f"Enabled: {enabled_count}")
        print(f"Disabled: {disabled_count}")
    
    return port_data


def main():
    parser = argparse.ArgumentParser(
        prog='gigamon-parser',
        description='Parse Gigamon "show diag" files to extract port inventory',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s show_diag.txt                    # Default table output
  %(prog)s show_diag.txt --format csv       # CSV output
  %(prog)s show_diag.txt --format json      # JSON output
  %(prog)s show_diag.txt --no-summary       # Hide summary counts
        '''
    )
    
    parser.add_argument(
        'file',
        help='Path to the Gigamon show diag file'
    )
    
    parser.add_argument(
        '-f', '--format',
        choices=['table', 'csv', 'json'],
        default='table',
        help='Output format (default: table)'
    )
    
    parser.add_argument(
        '--no-summary',
        action='store_true',
        help='Hide the summary counts'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    args = parser.parse_args()
    
    parse_gigamon_diag(
        file_path=args.file,
        output_format=args.format,
        show_summary=not args.no_summary
    )


if __name__ == "__main__":
    main()
