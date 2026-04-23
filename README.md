# Gigamon Show Diag Parser

A CLI tool to parse Gigamon `show diag` output files and extract port inventory information.

## Installation

```bash
# Clone the repo
git clone https://github.com/min-hsao/gigamon-diag-parser.git
cd gigamon-diag-parser

# Make it executable (optional)
chmod +x gigamon_parser.py

# Or install globally (optional)
ln -s $(pwd)/gigamon_parser.py /usr/local/bin/gigamon-parser
```

## Usage

```bash
# Basic usage - just pass the diag file
python gigamon_parser.py show_diag.txt

# Or if made executable
./gigamon_parser.py show_diag.txt
```

### Options

```
usage: gigamon-parser [-h] [-f {table,csv,json}] [--no-summary] [-v] file

Parse Gigamon "show diag" files to extract port inventory

positional arguments:
  file                  Path to the Gigamon show diag file

options:
  -h, --help            show this help message and exit
  -f, --format {table,csv,json}
                        Output format (default: table)
  --no-summary          Hide the summary counts
  -v, --version         show program's version number and exit
```

### Examples

```bash
# Default table output
gigamon-parser show_diag.txt

# CSV output (for Excel/spreadsheets)
gigamon-parser show_diag.txt --format csv > ports.csv

# JSON output (for scripting)
gigamon-parser show_diag.txt --format json

# Table without summary
gigamon-parser show_diag.txt --no-summary
```

### Output Formats

**Table (default):**
```
Port       Type         Alias                          Admin    Link     Speed  Media      RxUtil%  TxUtil%
-------------------------------------------------------------------------------------------------------------------
1/1/x1     network      -                              Disabled -        -      Fiber      0%       0%
1/1/x5     tool         To_IDS_Sensor_1                Enabled  Up       10Gb   Fiber      0%       14.14%
1/1/x7     tool         To_NTP_Monitor                 Enabled  Up       1Gb    Copper     0%       0%
1/1/x17    inline-net   To_Core_Switch_From_Router_1   Enabled  Up       10Gb   Fiber      0.76%    0.59%
1/2/e1     gs           -                              Enabled  Up       80000  No Module  0%       0%

--- Summary ---
Total Ports:          48
  Admin Enabled:      32
  Admin Disabled:     16

Enabled Port Breakdown:
  Network (OOB):      8
  Tool (OOB):         4
  Inline Network:     16  (8 pairs)
  Inline Tool:        0
  GS Engine:          1
  --------------------
  Total Enabled:      29

Link Status (enabled ports):
  Link Up:            28
  Link Down:          2
  No Link Info:       2
```

**CSV:**
```csv
Port,Type,Alias,Admin Status,Link Status,Speed,Media,RxUtil%,TxUtil%
1/1/x1,network,"",Disabled,-,-,Fiber,0.0000,0.0000
1/1/x5,tool,"To_IDS_Sensor_1",Enabled,Up,10Gb,Fiber,0.0000,14.1394
1/1/x7,tool,"To_NTP_Monitor",Enabled,Up,1Gb,Copper,0.0000,0.0000

SUMMARY,,,,,,,
Total Ports,48,,,,,,
Admin Enabled,32,,,,,,
Admin Disabled,16,,,,,,
Enabled Network (OOB),8,,,,,,
Enabled Tool (OOB),4,,,,,,
Enabled Inline Network,16,,,,,,
Enabled Inline Tool,0,,,,,,
Enabled GS Engine,1,,,,,,
Link Up,28,,,,,,
Link Down,2,,,,,,
```

**JSON:**
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
  },
  {
    "port": "1/1/x5",
    "type": "tool",
    "alias": "To_IDS_Sensor_1",
    "admin_status": "Enabled",
    "link_status": "Up",
    "speed": "10Gb",
    "media": "Fiber",
    "rx_util_pct": 0.0,
    "tx_util_pct": 14.1394
  }
]
```

## Information Extracted

| Field | Description |
|-------|-------------|
| Port | Port identifier (e.g., 1/1/x1, 1/2/e1, 1/2/q1) |
| Type | Port type — network, tool, inline-net, gs |
| Alias | Port alias from running config |
| Admin Status | Admin state — Enabled or Disabled |
| Link Status | Link state — Up, Down, or - (N/A) |
| Speed | Port speed (1Gb, 10Gb, 40Gb, 100Gb, 80000) |
| Media | Media type (Fiber, Copper, No Module) |
| Rx Util % | RX utilization percentage (from IfInOctetsPerSec) |
| Tx Util % | TX utilization percentage (from IfOutOctetsPerSec) |

## Port Types Detected

| Type | Description |
|------|-------------|
| `network` | Out-of-band network port |
| `tool` | Out-of-band tool port |
| `inline-net` | Inline network port (bypass pair) |
| `gs` | GigaSMART engine port |

## Requirements

- Python 3.6+
- No external dependencies (uses only standard library)

## License

MIT
