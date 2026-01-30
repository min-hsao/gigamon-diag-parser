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
Port       Type         Alias                               Status     Speed    Media          
-----------------------------------------------------------------------------------------------
1/1/x1     network      Uplink_To_Core_Switch               Enabled    10Gb     Fiber          
1/1/x2     network      Backup_Link                         Disabled   10Gb     No Module      
1/1/x3     tool         IDS_Monitor_Port                    Enabled    1Gb      Copper         

--- Summary ---
Total Ports Found: 48
Enabled: 32
Disabled: 16
```

**CSV:**
```csv
Port,Type,Alias,Status,Speed,Media
1/1/x1,network,"Uplink_To_Core_Switch",Enabled,10Gb,Fiber
1/1/x2,network,"Backup_Link",Disabled,10Gb,No Module
```

**JSON:**
```json
[
  {
    "port": "1/1/x1",
    "type": "network",
    "alias": "Uplink_To_Core_Switch",
    "status": "Enabled",
    "speed": "10Gb",
    "media": "Fiber"
  }
]
```

## Information Extracted

| Field | Description |
|-------|-------------|
| Port | Port identifier (e.g., 1/1/x1) |
| Type | Port type (network, tool, etc.) |
| Alias | Port alias from running config |
| Status | Admin status (Enabled/Disabled) |
| Speed | Port speed (1Gb, 10Gb, 40Gb, 100Gb) |
| Media | Media type (Fiber, Copper, No Module) |

## Requirements

- Python 3.6+
- No external dependencies (uses only standard library)

## License

MIT
