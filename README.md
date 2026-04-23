# Gigamon Show Diag Parser

Standalone CLI tool to parse Gigamon `show diag` output and extract structured port inventory data. Zero dependencies.

Used by the [Gigamon Migration Tool](https://github.com/min-hsao/gigamon-migration-tool) for HC2 migration analysis.

## Features

- **Full port inventory** — extracts all port types (network, tool, inline-net, gs, inline-tool)
- **Running config parsing** — inline networks, GigaSMART features, port aliases
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
  -v, --version         Show version number
```

## Output Formats

### Table (default)

```
Port       Type         Alias             Admin    Link    Speed  Media   RxUtil%  TxUtil%
--------------------------------------------------------------------------------------------
1/1/x1     network      -                 Disabled -       -      Fiber   0%       0%
1/1/x5     tool         To_ExtraHop_1     Enabled  Up      10Gb   Fiber   0%       14.14%
1/1/x17    inline-net   To_QFX_Core_1     Enabled  Up      10Gb   Fiber   0.76%    0.59%
1/2/e1     gs           -                 Enabled  Up      80000  N/A     0%       0%

--- Summary ---
Total Ports:          59
  Admin Enabled:      21
  Admin Disabled:     38

Enabled Port Breakdown:
  Network (OOB):      0
  Tool (OOB):         4
  Inline Network:     16  (8 pairs)
  GS Engine:          1
  Total Enabled:      21

Speed/Media (enabled):
  10G Fiber (SR):     18
  1G Copper:          2
```

### CSV

```csv
Port,Type,Alias,Admin Status,Link Status,Speed,Media,RxUtil%,TxUtil%
1/1/x1,network,,Disabled,-,-,Fiber,0.0000,0.0000
1/1/x5,tool,To_ExtraHop_1,Enabled,Up,10Gb,Fiber,0.0000,14.1394
```

### JSON

```json
[
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
]
```

## Data Extracted

| Field | Source Section | Description |
|-------|---------------|-------------|
| Port | Port Params | Port identifier (1/1/x1, 1/2/e1, 1/2/q1) |
| Type | Port Params | network, tool, inline-net, gs |
| Alias | Port Params + Running Config | Full alias from running config (not truncated) |
| Admin Status | Port Params | Enabled / Disabled |
| Link Status | Port Params | Up / Down / - (N/A) |
| Speed | Port Params | 1Gb, 10Gb, 40Gb, 100Gb |
| Media | SFP Type | Fiber, Copper, N/A |
| RX/TX Util % | IfInOctetsPerSec / IfOutOctetsPerSec | Current utilization percentage |

## Supported HW Types

Tested with `show diag` output from:

- **CHS-HC2** — GigaVUE-HC2 (EOL, migration source)
- **CHS-HC1** — GigaVUE-HC1
- GigaVUE-OS 6.x

## Requirements

- Python 3.6+
- No external dependencies

## License

MIT
