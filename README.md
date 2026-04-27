# Gigamon Show Diag Parser

Standalone CLI tool to parse Gigamon `show diag` output and extract structured port inventory, IP interfaces, and GigaSMART license data. Zero dependencies.

Used by the [Gigamon Migration Tool](https://github.com/min-hsao/gigamon-migration-tool) for HC2 migration analysis.

## Features

- **Full port inventory** — extracts all port types (network, tool, inline-net, gs, inline-tool, hybrid, stack)
- **IP interfaces** — physical (eth0/1/2, inband) and logical (netflow, tunnel, metadata)
- **GigaSMART licenses** — per-box, per-slot feature licenses with expiration status
- **Running config parsing** — inline networks, GigaSMART features, port aliases
- **Cluster support** — multi-node cluster detection with per-node port counts
- **Utilization data** — RX/TX utilization from interface counters
- **Multiple output formats** — table, CSV, JSON
- **Summary statistics** — enabled/disabled counts, link status, speed/media breakdown
- **No dependencies** — pure Python 3.6+ standard library

## Installation

```bash
git clone https://github.com/min-hsao/gigamon-diag-parser.git
cd gigamon-diag-parser
chmod +x gigamon_parser.py  # optional
```

## Usage

```bash
# Default table output
python3 gigamon_parser.py show_diag.txt

# CSV for spreadsheet import
python3 gigamon_parser.py show_diag.txt --format csv > ports.csv

# JSON for scripting/piping
python3 gigamon_parser.py show_diag.txt --format json

# Suppress summary counts
python3 gigamon_parser.py show_diag.txt --no-summary
```

### Options

```
usage: gigamon-parser [-h] [-f {table,csv,json}] [--no-summary] [-v] file

Parse Gigamon "show diag" files to extract port inventory

positional arguments:
  file                  Path to the Gigamon show diag file

options:
  -h, --help            show this message and exit
  -f, --format {table,csv,json}
                        Output format (default: table)
  --no-summary          Hide the summary counts
  -v, --version         Show version number (current: 1.3.0)
```

## Output Formats

### Table (default)

```
Port       Type         Alias             Admin    Link    Speed  Media   RxUtil%  TxUtil%
--------------------------------------------------------------------------------------------
1/1/x1     network      -                 Disabled -       -      Fiber   0%       0%
1/1/x5     tool         To_ExtraHop_1     Enabled  Up      10Gb   Fiber   0%       14.14%
1/1/x6     inline-net   To_Core_1         Enabled  Up      10Gb   Fiber   0.76%    0.59%
1/2/e1     gs           -                 Enabled  Up      80000  N/A     0%       0%

--- Summary ---
Cluster:              500P (4 nodes)
  Box 1: HC2 (CHS-HC2) - 40 ports (36 enabled)
  Box 2: STNMED2-MTR-TA40 (TA40-Chassis) - 32 ports (23 enabled)
Total Ports:          180
  Admin Enabled:      143
  Admin Disabled:     37

Enabled Port Breakdown:
  Network (OOB):      91
  Tool (OOB):         22
  Inline Network:     0
  GS Engine:          2
  Hybrid:             2
  Stack:              26

--- IP Interfaces ---
  Name                                IP/Mask              Type         Admin  Oper   Ports
  ----------------------------------- -------------------- ------------ ------ ------ ------
  eth0                                10.147.230.51/24     management   up     up
    alias: 10.147.230.50/24 (alias: 'eth0:0')
  eth1                                N/A                  management   down   down
  Netflow-Interface                   10.147.230.54/24     netflow                    1/4/x4
    gsgroup=GS24  exporter=NF-EXP-4
  giga_auto_tunnel_1_2_x4             10.145.200.7/23      tunnel                     1/2/x4

--- GigaSMART Licenses ---
  Box 1    slot=2        dedup                status=perpetual
  Box 1    slot=2        netflow              status=expired
  Box 1    slot=2        masking              status=perpetual
  Box 2    slot=chassis  ADV_FEATURES         status=perpetual
```

### CSV

```csv
Port,Type,Alias,Admin Status,Link Status,Speed,Media,RxUtil%,TxUtil%
1/1/x1,network,,Disabled,-,-,Fiber,0.0000,0.0000
1/1/x5,tool,To_ExtraHop_1,Enabled,Up,10Gb,Fiber,0.0000,14.1394
```

### JSON

```json
{
  "ports": [
    {
      "port": "1/1/x1",
      "type": "network",
      "alias": "",
      "admin_status": "Disabled",
      "link_status": "-",
      "speed": "-",
      "media": "Fiber",
      "rx_util_pct": 0.0,
      "tx_util_pct": 0.0
    }
  ],
  "ip_interfaces": [
    {
      "name": "eth0",
      "ip_mask": "10.147.230.51/24",
      "interface_type": "management",
      "admin_status": "up",
      "oper_status": "up"
    }
  ],
  "logical_ip_interfaces": [
    {
      "name": "Netflow-Interface",
      "ip_mask": "10.147.230.54/24",
      "interface_type": "netflow",
      "ports": "1/4/x4",
      "gsgroup": "GS24",
      "exporter": "NF-EXP-4"
    }
  ],
  "all_ip_interfaces": [ "... merged physical + logical ..." ],
  "gs_licenses": [
    {
      "box": 1,
      "slot": 2,
      "feature": "dedup",
      "parameters": "-",
      "start_date": "2025/01/30",
      "expiration": "Never"
    }
  ],
  "cluster": {
    "is_cluster": true,
    "cluster_name": "500P",
    "node_count": 4,
    "nodes": [ "..." ]
  },
  "summary": {
    "total_ports": 180,
    "admin_enabled": 143,
    "link_up": 101,
    "link_down": 42
  }
}
```

## Data Extracted

### Port Inventory

| Field | Source Section | Description |
|-------|---------------|-------------|
| Port | Port Params | Port identifier (1/1/x1, 1/2/e1, 1/2/q1) |
| Type | Port Params | network, tool, inline-net, gs, hybrid, stack |
| Alias | Running Config | Full alias from running config |
| Admin Status | Port Params | Enabled / Disabled |
| Link Status | Port Params | Up / Down / - (N/A) |
| Speed | Port Params | 1Gb, 10Gb, 40Gb, 100Gb |
| Media | SFP Type | Fiber, Copper, No Module |
| RX/TX Util % | Interface Counters | Current utilization percentage |

### IP Interfaces

| Field | Description |
|-------|-------------|
| Name | Interface name (eth0, Netflow-Interface, giga_auto_tunnel_*) |
| IP/Mask | IPv4 address with CIDR notation |
| Interface Type | management, netflow, tunnel, metadata, inband, discovery |
| Admin Status | up / down |
| Oper Status | up / down |
| Ports | Associated data port(s) |
| GigaSMART Group | GS group assignment |
| Exporter | Netflow/metadata exporter name |

### GigaSMART Licenses

| Field | Description |
|-------|-------------|
| Box | Cluster box ID |
| Slot | Module slot number or "chassis" for TA-series |
| Feature | License feature name (dedup, netflow, masking, tunneling, etc.) |
| Parameters | License parameters |
| Start Date | License activation date |
| Expiration | Expiration date, "Never" (perpetual), or "expired" |

## Supported HW Types

Tested with `show diag` output from:

- **CHS-HC2** — GigaVUE-HC2 (EOL, migration source)
- **CHS-HC1** — GigaVUE-HC1
- **TA10-Chassis** — GigaVUE-TA10
- **TA25-Chassis** — GigaVUE-TA25
- **TA40-Chassis** — GigaVUE-TA40
- Cluster configurations (multi-node)
- GigaVUE-OS 5.x and 6.x

## Requirements

- Python 3.6+
- No external dependencies

## License

MIT
