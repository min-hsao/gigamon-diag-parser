#!/usr/bin/env python3
"""
Gigamon 'show diag' Parser
Parses Gigamon diagnostic files to extract port inventory and utilization.
"""

import argparse
import re
import sys
import json

def parse_gigamon_diag(file_path, output_format='table', show_summary=True):
    """
    Parses a Gigamon 'show diag' file to extract port inventory.
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
                        "Media": "N/A",
                        "RxRate": "0",
                        "TxRate": "0"
                    }
            continue

        if line.startswith("=") or not current_ports:
            continue

        parts = re.split(r'\s{2,}', line)
        if len(parts) < 2: continue
            
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
                    port_data[current_ports[i]]["SFP"] = val
                    media = "Unknown"
                    val_lower = val.lower()
                    if "cu" in val_lower or "copper" in val_lower: media = "Copper"
                    elif any(x in val_lower for x in ['sx', 'lx', 'sr', 'lr', 'er', 'zr']): media = "Fiber"
                    elif "qsfp" in val_lower: media = "Fiber (QSFP)"
                    elif val_lower in ["none", "n/a", "(unsupported)"]: media = "No Module"
                    else: media = val
                    port_data[current_ports[i]]["Media"] = media

    # --- STEP 2.5: Parse Port Statistics Table ---
    current_stats_ports = []
    stats_header_pattern = re.compile(r'^\s*Counter Name\s+(.*)')
    
    for line in lines:
        line = line.strip()
        match = stats_header_pattern.match(line)
        if match:
            raw_ports = re.split(r'\s{2,}', match.group(1))
            current_stats_ports = []
            for p_str in raw_ports:
                p_id = p_str.replace("Port:", "").strip()
                current_stats_ports.append(p_id)
            continue

        if line.startswith("=") or not current_stats_ports:
            continue
            
        parts = re.split(r'\s{2,}', line)
        if len(parts) < 2: continue
        
        label = parts[0].replace(":", "").strip()
        values = parts[1:]
        
        if label == "IfInOctetsPerSec":
            for i, val in enumerate(values):
                if i < len(current_stats_ports):
                    p = current_stats_ports[i]
                    if p in port_data:
                        port_data[p]["RxRate"] = val
        elif label == "IfOutOctetsPerSec":
            for i, val in enumerate(values):
                if i < len(current_stats_ports):
                    p = current_stats_ports[i]
                    if p in port_data:
                        port_data[p]["TxRate"] = val

    # --- STEP 3: Formatting Output ---
    
    def calc_util(rate_str, speed_str):
        try:
            rate = float(rate_str)
            if speed_str in ["N/A", "Unknown", "-"]: return 0.0
            
            # Rough speed mapping based on standard Gigamon output
            speed_bps = 0
            if "100Gb" in speed_str: speed_bps = 100_000_000_000
            elif "40Gb" in speed_str: speed_bps = 40_000_000_000
            elif "10Gb" in speed_str: speed_bps = 10_000_000_000
            elif "1Gb" in speed_str: speed_bps = 1_000_000_000
            elif "100Mb" in speed_str: speed_bps = 100_000_000
            else: return 0.0
            
            # (Bytes * 8) / Speed
            if speed_bps == 0: return 0.0
            util = (rate * 8 * 100) / speed_bps
            return util
        except (ValueError, TypeError):
            return 0.0

    def natural_keys(text):
        return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', text)]

    sorted_ports = sorted(port_data.keys(), key=natural_keys)
    
    if output_format == 'json':
        output = []
        for port in sorted_ports:
            data = port_data[port]
            rx_util = calc_util(data["RxRate"], data["Speed"])
            tx_util = calc_util(data["TxRate"], data["Speed"])
            output.append({
                "port": port,
                "type": data["Type"].replace("(T)", ""),
                "alias": port_aliases.get(port, ""),
                "status": data["Admin"].capitalize(),
                "speed": data["Speed"],
                "media": data["Media"],
                "rx_util_pct": round(rx_util, 4),
                "tx_util_pct": round(tx_util, 4)
            })
        print(json.dumps(output, indent=2))
        
    elif output_format == 'csv':
        print("Port,Type,Alias,Status,Speed,Media,RxUtil%,TxUtil%")
        for port in sorted_ports:
            data = port_data[port]
            alias = port_aliases.get(port, "").replace(",", ";")
            p_type = data["Type"].replace("(T)", "")
            status = data["Admin"].capitalize()
            
            rx_util = calc_util(data["RxRate"], data["Speed"])
            tx_util = calc_util(data["TxRate"], data["Speed"])
            
            print(f'{port},{p_type},"{alias}",{status},{data["Speed"]},{data["Media"]},{rx_util:.4f},{tx_util:.4f}')
        
        # Add summary rows
        enabled_count = sum(1 for p in port_data.values() if p["Admin"].lower() == "enabled")
        disabled_count = sum(1 for p in port_data.values() if p["Admin"].lower() == "disabled")
        print("")
        print(f"SUMMARY,,,,,,,")
        print(f"Total Ports,{len(port_data)},,,,,,")
        print(f"Enabled,{enabled_count},,,,,,")
        print(f"Disabled,{disabled_count},,,,,,")
            
    else:  # table format
        print(f"{'Port':<10} {'Type':<12} {'Alias':<30} {'Status':<8} {'Speed':<6} {'Media':<10} {'RxUtil%':<8} {'TxUtil%':<8}")
        print("-" * 105)

        for port in sorted_ports:
            data = port_data[port]
            alias = port_aliases.get(port, "-")
            status = data["Admin"].capitalize()
            p_type = data["Type"].replace("(T)", "")
            
            rx_util = calc_util(data["RxRate"], data["Speed"])
            tx_util = calc_util(data["TxRate"], data["Speed"])
            
            rx_str = f"{rx_util:.2f}%" if rx_util > 0 else "0%"
            tx_str = f"{tx_util:.2f}%" if tx_util > 0 else "0%"

            print(f"{port:<10} {p_type:<12} {alias:<30} {status:<8} {data['Speed']:<6} {data['Media']:<10} {rx_str:<8} {tx_str:<8}")

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
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('file', help='Path to the Gigamon show diag file')
    parser.add_argument('-f', '--format', choices=['table', 'csv', 'json'], default='table', help='Output format')
    parser.add_argument('--no-summary', action='store_true', help='Hide the summary counts')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.1.0')
    
    args = parser.parse_args()
    
    parse_gigamon_diag(
        file_path=args.file,
        output_format=args.format,
        show_summary=not args.no_summary
    )

if __name__ == "__main__":
    main()
