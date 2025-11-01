# 🔍 Unused Function Detector

A powerful Python tool that uses Language Server Protocol (LSP) to accurately detect unused functions in your codebase.

## 📖 Usage

### Basic Usage
```bash
# Scan current directory
ufd check .

# Scan specific path
ufd check ./my-project
```

### Output Formats

#### Tree (default)
Beautiful hierarchical tree view with colors:
```
🔍 Unused functions by file (total 3 functions)
├── 📁 src/
│   ├── 📄 utils.py
│   │   └── 🟣 helper_func (line 15)
│   └── 📄 main.py
│       └── 🟣 old_function (line 42)
└── 📄 config.py
    └── 🟣 debug_config (line 8)

📊 Summary:
   Files scanned: 12
   Unused functions: 3
   Scan duration: 1.23s
```

#### JSON
Structured data for programmatic use:
```json
{
  "summary": {
    "files_scanned": 12,
    "total_functions": 45,
    "unused_functions_count": 3,
    "scan_duration": 1.23
  },
  "unused_functions": [
    {
      "file_uri": "file:///path/to/utils.py",
      "name": "helper_func",
      "line": 15,
      "character": 4
    }
  ]
}
```

#### CSV
Tabular format for spreadsheet analysis:
```csv
File,Function,Line,Character
/path/to/utils.py,helper_func,15,4
/path/to/main.py,old_function,42,4
```
