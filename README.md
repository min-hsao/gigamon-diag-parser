# Gigamon Show Diag Parser

A Python utility to parse Gigamon `show diag` output files and extract port inventory information in a clean, readable format.

## Features

- Parses Gigamon diagnostic files to extract port information
- Extracts full port aliases from running configuration (handles truncated aliases)
- Shows port type, status, speed, SFP type, and media type
- Natural sorting of ports (x1, x2, x10 instead of x1, x10, x2)
- Summary counts of enabled/disabled ports

## Usage

```bash
python gigamon_parser.py <show_diag_file>
```

### Example

```bash
python gigamon_parser.py gigamon_show_diag.txt
```

### Output

```
Port       Type         Alias                               Status     Speed    Media          
-----------------------------------------------------------------------------------------------
1/1/x1     network      Uplink_To_Core_Switch               Enabled    10Gb     Fiber          
1/1/x2     network      Backup_Link                         Disabled   10Gb     No Module      
1/1/x3     tool         IDS_Monitor_Port                    Enabled    1Gb      Copper         
...

--- Summary ---
Total Ports Found: 48
Enabled: 32
Disabled: 16
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
