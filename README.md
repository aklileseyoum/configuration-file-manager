# Configuration File Manager

A command-line tool that reads configuration files in **JSON, CSV and XML**, validates them against a schema, converts between formats, discovers config files in a folder, and keeps backups of overwritten files.

## Features
- Read and write JSON, CSV and XML through one common interface (`Protocol`).
- Schema validation with `TypedDict`: required fields, empty keys, duplicate `(section, key)` pairs.
- Conversion between any two formats using a functional pipeline (`filter` then `map`).
- File discovery with `pathlib` (`glob` / `rglob`).
- Generators that stream entries one at a time, so large files stay out of memory.
- Transactional writes: a failed conversion never corrupts the original file.
- Automatic timestamped backups (`.bak`) of overwritten files.
- Custom exception hierarchy, so expected failures give a clear message instead of a traceback.

## Requirements
- Python 3.11 or newer
- [Poetry](https://python-poetry.org/)

## Setup
```powershell
git clone <repository-url>
cd configuration-file-manager
poetry install
poetry run pytest -q
```
Without Poetry: `pip install -r requirements.txt` (development tools only; the application uses the standard library).

## Usage
```powershell
poetry run python -m config_file_manager.cli list samples
poetry run python -m config_file_manager.cli validate samples\app.json
poetry run python -m config_file_manager.cli convert samples\app.json output\app.xml
```

### Sample session
```
> poetry run python -m config_file_manager.cli convert samples\app.json output\app.xml
INFO: Converted samples\app.json -> output\app.xml (4 entries)
Converted 4 entries to output\app.xml
```

### Sample error
```
> poetry run python -m config_file_manager.cli validate samples\invalid.json
Error: Entry is missing fields: value
```
The exit code is 1 on any error and 0 on success.

## Format support matrix
| Format | Read | Write | Streaming (generator) | Library |
|---|---|---|---|---|
| JSON (`.json`) | yes | yes | no (`json.load` reads the whole file) | `json` |
| CSV (`.csv`) | yes | yes | yes, row by row | `csv.DictReader` / `DictWriter` |
| XML (`.xml`) | yes | yes | yes, incremental | `xml.etree.ElementTree.iterparse` |

## Schema definitions
A config is a flat list of entries:
```python
class ConfigEntry(TypedDict):
    section: str   # required, not empty
    key: str       # required, not empty
    value: str     # required (may be empty)
```

| Format | Layout |
|---|---|
| JSON | `{"entries": [{"section": "database", "key": "port", "value": "5432"}]}` |
| CSV | header `section,key,value`, one entry per row |
| XML | `<config><entry section="database" key="port">5432</entry></config>` |

Validation rules: entries must contain `section`, `key` and `value`; `section` and `key` must not be empty; whitespace is stripped; the same `(section, key)` pair must not appear twice in one file.

## Conversion examples
`samples\app.json` converted to XML:
```xml
<?xml version='1.0' encoding='utf-8'?>
<config>
  <entry section="database" key="host">localhost</entry>
  <entry section="database" key="port">5432</entry>
  <entry section="server" key="debug">true</entry>
  <entry section="server" key="workers">4</entry>
</config>
```
The same content converted to CSV:
```csv
section,key,value
database,host,localhost
database,port,5432
server,debug,true
server,workers,4
```
During conversion, entries with an empty value are dropped (`filter`) and section and key are lowercased (`map`). Content is preserved across all three formats (checked by tests).

## Project structure
| File | Responsibility |
|---|---|
| `exceptions.py` | Custom exceptions (`ConfigError` base) |
| `schema.py` | `ConfigEntry` TypedDict and validation |
| `handlers.py` | `FormatHandler` Protocol and the JSON, CSV and XML handlers |
| `manager.py` | Discovery, loading, validation, conversion, transactions, backups |
| `cli.py` | Command-line interface (`list`, `validate`, `convert`) |

## Design decisions
- **`Protocol` for handlers:** any class with `iter_entries` and `write` is a handler, with no inheritance needed. Adding YAML later means one new class and one registry line.
- **Generators:** `iter_entries` yields one entry at a time. `load_config` collects them into a list only when needed.
- **Transactions:** `config_transaction` writes to a `.tmp` file and replaces the target only if the block succeeds.
- **Backups:** an existing destination is copied to `<name>.<timestamp>.bak` before it is overwritten.
- **One exception hierarchy:** the CLI catches `ConfigError` once and prints a clean message.

## Memory usage comparison
Measured with `tracemalloc` (`poetry run python scripts/memory_report.py`), 100,000 entries per file, peak memory. These are the numbers from my machine during development; your run will differ slightly:

| Format | Load all into a list | Stream with the generator |
|---|---|---|
| CSV | 32,311 KiB | 47 KiB |
| XML | 28,171 KiB | 245 KiB |

Streaming keeps memory almost flat however large the file is. For XML, the root element must be cleared as entries are processed; clearing only the entry leaves empty elements attached to the root and memory keeps growing.

## Testing
```powershell
poetry run pytest -q --cov=config_file_manager --cov-branch
```
32 tests, 97% line and branch coverage: reading, writing and round-tripping each format, malformed JSON, XML and CSV, schema validation, generator behavior, discovery, duplicate keys, conversion between formats, backups, transaction commit and rollback, and the CLI.

## Code quality
```powershell
poetry run mypy src
poetry run ruff check src tests
```

## Known limitations
- JSON is loaded whole (the standard library has no streaming JSON parser).
- The layout is a flat list of sections and keys, not nested configuration.
