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
    Supports standalone and multi-appliance cluster outputs.
    """
    
    # Dictionaries to store data
    port_aliases = {}
    port_data = {}
    cluster_info = {
        "is_cluster": False,
        "cluster_id": "",
        "cluster_name": "",
        "node_count": 0,
        "nodes": []
    }

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.", file=sys.stderr)
        sys.exit(1)

    # --- STEP 0: Detect/parse cluster metadata ---
    text = ''.join(lines)
    node_count_m = re.search(r'Cluster node count:\s+(\d+)', text)
    if node_count_m and int(node_count_m.group(1)) > 1:
        cluster_info["is_cluster"] = True
        cluster_info["node_count"] = int(node_count_m.group(1))
        m = re.search(r'Cluster ID:\s+(\S+)', text)
        if m:
            cluster_info["cluster_id"] = m.group(1)
        m = re.search(r'Cluster name:\s+(\S+)', text)
        if m:
            cluster_info["cluster_name"] = m.group(1)

        chassis_m = re.search(r'-+Chassis-+\n.*?\n-+\n(.*?)(?=\n\n)', text, re.DOTALL)
        if chassis_m:
            row_pat = re.compile(r'^\s*(\d+)\s*\*?\s+(\S+)\s+yes\s+up\s+(\S+)\s+(\S+)\s+(\S+)', re.MULTILINE)
            nodes = {}
            for rm in row_pat.finditer(chassis_m.group(1)):
                bid = rm.group(1)
                nodes[bid] = {
                    "box_id": int(bid),
                    "hostname": rm.group(2),
                    "hw_type": rm.group(3),
                    "product_code": rm.group(4),
                    "serial_number": rm.group(5),
                    "total_ports": 0,
                    "enabled_ports": 0,
                    "network_ports": 0,
                    "tool_ports": 0,
                    "inline_network_ports": 0,
                    "inline_tool_ports": 0,
                    "gs_ports": 0,
                }
            cluster_info["nodes"] = [nodes[k] for k in sorted(nodes.keys(), key=int)]

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
    header_pattern = re.compile(r'^\s*Parameter\s+([0-9]+/\d+/\S+.*)')
    
    valid_param_labels = {"Type", "Admin", "Link status", "Speed (Mbps)", "SFP type"}

    for raw_line in lines:
        line = raw_line.strip()
        
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

        # End the current Parameter table when another section starts
        if line.startswith("-----------------------------------") or line.startswith("#=================================="):
            current_ports = []
            continue

        if line.startswith("=") or not current_ports:
            continue

        parts = re.split(r'\s{2,}', line)
        if len(parts) < 2:
            continue
            
        raw_label = parts[0].strip()
        label = raw_label.replace(":", "").strip()
        values = parts[1:]

        # Only parse actual Port Params rows; ignore trailing stats/other text
        if raw_label.rstrip(':') not in valid_param_labels and label not in valid_param_labels:
            continue
        
        if label == "Type": 
            for i, val in enumerate(values):
                if i < len(current_ports):
                    port_data[current_ports[i]]["Type"] = val
        elif label == "Admin":
            for i, val in enumerate(values):
                if i < len(current_ports):
                    port_data[current_ports[i]]["Admin"] = val
        elif "Link status" in label:
            for i, val in enumerate(values):
                if i < len(current_ports):
                    port_data[current_ports[i]]["Link"] = val
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

    # Populate cluster per-node counts
    if cluster_info["is_cluster"] and cluster_info["nodes"]:
        node_map = {str(n["box_id"]): n for n in cluster_info["nodes"]}
        for port, data in port_data.items():
            box_id = port.split('/')[0] if '/' in port else None
            if box_id in node_map:
                node = node_map[box_id]
                node["total_ports"] += 1
                if data["Admin"].lower() == "enabled":
                    node["enabled_ports"] += 1
                ptype = data["Type"].lower()
                if ptype == "network":
                    node["network_ports"] += 1
                elif ptype == "tool":
                    node["tool_ports"] += 1
                elif ptype in ("inline-net", "inline-network"):
                    node["inline_network_ports"] += 1
                elif ptype in ("inline-tool",):
                    node["inline_tool_ports"] += 1
                elif ptype in ("gs", "gigasmart", "gs-engine"):
                    node["gs_ports"] += 1

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
                "admin_status": data["Admin"].capitalize(),
                "link_status": data.get("Link", "N/A").capitalize(),
                "speed": data["Speed"],
                "sfp_type": data["SFP"],
                "media": data["Media"],
                "rx_util_pct": round(rx_util, 4),
                "tx_util_pct": round(tx_util, 4)
            })
        json_payload = {"ports": output}
        if cluster_info["is_cluster"]:
            json_payload["cluster"] = cluster_info
        if show_summary:
            enabled_count = sum(1 for p in port_data.values() if p["Admin"].lower() == "enabled")
            disabled_count = sum(1 for p in port_data.values() if p["Admin"].lower() == "disabled")
            link_up = sum(1 for p, d in port_data.items() if d["Admin"].lower() == "enabled" and d.get("Link", "").lower() == "up")
            link_down = sum(1 for p, d in port_data.items() if d["Admin"].lower() == "enabled" and d.get("Link", "").lower() == "down")
            sfp_breakdown = {}
            for d in port_data.values():
                sfp = d.get("SFP", "N/A") or "N/A"
                if sfp not in sfp_breakdown:
                    sfp_breakdown[sfp] = {"total": 0, "enabled": 0, "enabled_up": 0, "enabled_down": 0}
                sfp_breakdown[sfp]["total"] += 1
                if d["Admin"].lower() == "enabled":
                    sfp_breakdown[sfp]["enabled"] += 1
                    if d.get("Link", "").lower() == "up":
                        sfp_breakdown[sfp]["enabled_up"] += 1
                    elif d.get("Link", "").lower() == "down":
                        sfp_breakdown[sfp]["enabled_down"] += 1
            json_payload["summary"] = {
                "total_ports": len(port_data),
                "admin_enabled": enabled_count,
                "admin_disabled": disabled_count,
                "link_up": link_up,
                "link_down": link_down,
                "sfp_type_breakdown": sfp_breakdown,
            }
        print(json.dumps(json_payload, indent=2))
        
    elif output_format == 'csv':
        print("Port,Type,Alias,Admin Status,Link Status,Speed,SFP Type,RxUtil%,TxUtil%")
        for port in sorted_ports:
            data = port_data[port]
            alias = port_aliases.get(port, "").replace(",", ";")
            p_type = data["Type"].replace("(T)", "")
            admin_status = data["Admin"].capitalize()
            link_status = data.get("Link", "N/A").capitalize()
            
            rx_util = calc_util(data["RxRate"], data["Speed"])
            tx_util = calc_util(data["TxRate"], data["Speed"])
            
            print(f'{port},{p_type},"{alias}",{admin_status},{link_status},{data["Speed"]},{data["SFP"]},{rx_util:.4f},{tx_util:.4f}')
        
        # Add summary rows
        enabled_count = sum(1 for p in port_data.values() if p["Admin"].lower() == "enabled")
        disabled_count = sum(1 for p in port_data.values() if p["Admin"].lower() == "disabled")
        
        # summary now printed below in unified section
            
    else:  # table / CLI format
        def fmt(text, width):
            text = str(text) if text not in (None, "") else "-"
            return text if len(text) <= width else text[:max(1, width-3)] + "..."

        header = f"{'Port':<10} {'Type':<10} {'Alias':<34} {'Admin':<8} {'Link':<6} {'Speed':<7} {'SFP Type':<16} {'Rx':>7} {'Tx':>7}"
        rule = "-" * len(header)
        print(header)
        print(rule)

        current_box = None
        for port in sorted_ports:
            data = port_data[port]
            alias = port_aliases.get(port, "-")
            admin_status = data["Admin"].capitalize()
            link_status = data.get("Link", "N/A").capitalize()
            p_type = data["Type"].replace("(T)", "")
            
            rx_util = calc_util(data["RxRate"], data["Speed"])
            tx_util = calc_util(data["TxRate"], data["Speed"])
            
            rx_str = f"{rx_util:.2f}%" if rx_util > 0 else "0%"
            tx_str = f"{tx_util:.2f}%" if tx_util > 0 else "0%"

            # Group cluster output by box for cleaner CLI readability
            box_id = port.split('/')[0] if '/' in port else None
            if cluster_info["is_cluster"] and box_id != current_box:
                current_box = box_id
                node = next((n for n in cluster_info["nodes"] if str(n["box_id"]) == box_id), None)
                if node:
                    print()
                    print(f"[Box {node['box_id']}] {node['hostname']} ({node['hw_type']})")
                    print(rule)

            print(
                f"{port:<10} {fmt(p_type,10):<10} {fmt(alias,36):<36} "
                f"{fmt(admin_status,8):<8} {fmt(link_status,6):<6} {fmt(data['Speed'],7):<7} "
                f"{fmt(data['SFP'],16):<16} {rx_str:>7} {tx_str:>7}"
            )

    # --- Summary ---
    if show_summary:
        enabled_count = sum(1 for p in port_data.values() if p["Admin"].lower() == "enabled")
        disabled_count = sum(1 for p in port_data.values() if p["Admin"].lower() == "disabled")
        link_up = sum(1 for p, d in port_data.items() if d["Admin"].lower() == "enabled" and d.get("Link", "").lower() == "up")
        link_down = sum(1 for p, d in port_data.items() if d["Admin"].lower() == "enabled" and d.get("Link", "").lower() == "down")
        link_na = enabled_count - link_up - link_down

        # Count by type (enabled ports only)
        en_net = sum(1 for p, d in port_data.items() if d["Admin"].lower() == "enabled" and d["Type"].lower() == "network")
        en_tool = sum(1 for p, d in port_data.items() if d["Admin"].lower() == "enabled" and d["Type"].lower() == "tool")
        en_inline_net = sum(1 for p, d in port_data.items() if d["Admin"].lower() == "enabled" and d["Type"].lower() in ("inline-net", "inline-network"))
        en_inline_tool = sum(1 for p, d in port_data.items() if d["Admin"].lower() == "enabled" and d["Type"].lower() in ("inline-tool", "inline-tool"))
        en_gs = sum(1 for p, d in port_data.items() if d["Admin"].lower() == "enabled" and d["Type"].lower() in ("gs", "gigasmart", "gs-engine"))

        # Count by type (all ports)
        all_net = sum(1 for d in port_data.values() if d["Type"].lower() == "network")
        all_tool = sum(1 for d in port_data.values() if d["Type"].lower() == "tool")
        all_inline_net = sum(1 for d in port_data.values() if d["Type"].lower() in ("inline-net", "inline-network"))
        all_inline_tool = sum(1 for d in port_data.values() if d["Type"].lower() in ("inline-tool",))
        all_gs = sum(1 for d in port_data.values() if d["Type"].lower() in ("gs", "gigasmart", "gs-engine"))

        # SFP type breakdown
        sfp_breakdown = {}
        for d in port_data.values():
            sfp = d.get("SFP", "N/A") or "N/A"
            if sfp not in sfp_breakdown:
                sfp_breakdown[sfp] = {"total": 0, "enabled": 0, "enabled_up": 0, "enabled_down": 0}
            sfp_breakdown[sfp]["total"] += 1
            if d["Admin"].lower() == "enabled":
                sfp_breakdown[sfp]["enabled"] += 1
                if d.get("Link", "").lower() == "up":
                    sfp_breakdown[sfp]["enabled_up"] += 1
                elif d.get("Link", "").lower() == "down":
                    sfp_breakdown[sfp]["enabled_down"] += 1

        if output_format == 'table':
            print()
            print("--- Summary ---")
            if cluster_info["is_cluster"]:
                print(f"Cluster:              {cluster_info['cluster_name'] or cluster_info['cluster_id']} ({cluster_info['node_count']} nodes)")
                for node in cluster_info["nodes"]:
                    print(f"  Box {node['box_id']}: {node['hostname']} ({node['hw_type']}) - {node['total_ports']} ports ({node['enabled_ports']} enabled)")
            print(f"Total Ports:          {len(port_data)}")
            print(f"  Admin Enabled:      {enabled_count}")
            print(f"  Admin Disabled:     {disabled_count}")
            print()
            print("Enabled Port Breakdown:")
            print(f"  Network (OOB):      {en_net}")
            print(f"  Tool (OOB):         {en_tool}")
            if en_inline_net > 0:
                pairs = en_inline_net // 2
                print(f"  Inline Network:     {en_inline_net}  ({pairs} pair{'s' if pairs != 1 else ''})")
            else:
                print(f"  Inline Network:     0")
            if en_inline_tool > 0:
                tpairs = en_inline_tool // 2
                print(f"  Inline Tool:        {en_inline_tool}  ({tpairs} pair{'s' if tpairs != 1 else ''})")
            else:
                print(f"  Inline Tool:        0")
            print(f"  GS Engine:          {en_gs}")
            print(f"  {'-' * 20}")
            print(f"  Total Enabled:      {en_net + en_tool + en_inline_net + en_inline_tool + en_gs}")
            print()
            print("Link Status (enabled ports):")
            print(f"  Link Up:            {link_up}")
            print(f"  Link Down:          {link_down}")
            if link_na > 0:
                print(f"  No Link Info:       {link_na}")

            print()
            print("SFP Type Breakdown:")
            print(f"{'SFP Type':<20} {'Total':>7} {'Enabled':>9} {'Enabled Up':>11} {'Enabled Down':>13}")
            print("-" * 64)
            for sfp in sorted(sfp_breakdown.keys(), key=lambda x: x.lower()):
                row = sfp_breakdown[sfp]
                sfp_disp = sfp if len(sfp) <= 20 else sfp[:17] + '...'
                print(f"{sfp_disp:<20} {row['total']:>7} {row['enabled']:>9} {row['enabled_up']:>11} {row['enabled_down']:>13}")

        elif output_format == 'csv':
            print()
            print("SUMMARY,,,,,,,,")
            if cluster_info["is_cluster"]:
                print(f"Cluster,{cluster_info['cluster_name'] or cluster_info['cluster_id']},,,,,,,")
                print(f"Cluster Nodes,{cluster_info['node_count']},,,,,,,")
                for node in cluster_info["nodes"]:
                    print(f"Box {node['box_id']} {node['hostname']} ({node['hw_type']}),{node['total_ports']},enabled={node['enabled_ports']},network={node['network_ports']},tool={node['tool_ports']},inline-net={node['inline_network_ports']},inline-tool={node['inline_tool_ports']},gs={node['gs_ports']}")
            print(f"Total Ports,{len(port_data)},,,,,,,")
            print(f"Admin Enabled,{enabled_count},,,,,,,")
            print(f"Admin Disabled,{disabled_count},,,,,,,")
            print(f"Enabled Network (OOB),{en_net},,,,,,,")
            print(f"Enabled Tool (OOB),{en_tool},,,,,,,")
            print(f"Enabled Inline Network,{en_inline_net},,,,,,,")
            print(f"Enabled Inline Tool,{en_inline_tool},,,,,,,")
            print(f"Enabled GS Engine,{en_gs},,,,,,,")
            print(f"Link Up,{link_up},,,,,,,")
            print(f"Link Down,{link_down},,,,,,,")
            print("SFP Type,Total,Enabled,Enabled Up,Enabled Down,,,,")
            for sfp in sorted(sfp_breakdown.keys(), key=lambda x: x.lower()):
                row = sfp_breakdown[sfp]
                print(f"{sfp},{row['total']},{row['enabled']},{row['enabled_up']},{row['enabled_down']},,,,")

        elif output_format == 'json':
            # JSON summary is already printed as array; we add a summary object
            pass  # JSON callers can compute from the array

    if show_summary and output_format == 'json':
        pass  # JSON output is the array; summary is derivable
    
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
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.2.0')
    
    args = parser.parse_args()
    
    parse_gigamon_diag(
        file_path=args.file,
        output_format=args.format,
        show_summary=not args.no_summary
    )

if __name__ == "__main__":
    main()
