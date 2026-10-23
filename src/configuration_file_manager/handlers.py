"""Format handlers. Each one satisfies the FormatHandler Protocol.

`iter_entries` is a generator: it yields one entry at a time, so a huge
file never has to be held in memory. `read` simply collects it into a list.
"""

import csv
import json
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Protocol

from configuration_file_manager.exceptions import ConfigParseError
from configuration_file_manager.schema import (
    REQUIRED_FIELDS,
    ConfigEntry,
    validate_entry,
)


class FormatHandler(Protocol):
    """Anything with these methods is a format handler (structural typing)."""

    def iter_entries(self, path: Path) -> Iterator[ConfigEntry]: ...

    def write(self, entries: Iterable[ConfigEntry], path: Path) -> None: ...


class JsonHandler:
    """JSON layout: {"entries": [{"section": ..., "key": ..., "value": ...}]}"""

    def iter_entries(self, path: Path) -> Iterator[ConfigEntry]:
        with open(path, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as err:
                raise ConfigParseError(f"Invalid JSON in {path}: {err}") from err
        if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
            raise ConfigParseError(f"{path}: expected an object with an 'entries' list")
        for raw in data["entries"]:
            yield validate_entry(raw)

    def write(self, entries: Iterable[ConfigEntry], path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"entries": list(entries)}, f, indent=2)


class CsvHandler:
    """CSV layout: header `section,key,value`, one entry per row."""

    def iter_entries(self, path: Path) -> Iterator[ConfigEntry]:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or not set(REQUIRED_FIELDS) <= set(
                reader.fieldnames
            ):
                raise ConfigParseError(
                    f"{path}: header must contain {', '.join(REQUIRED_FIELDS)}"
                )
            for row in reader:
                yield validate_entry(row)

    def write(self, entries: Iterable[ConfigEntry], path: Path) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(REQUIRED_FIELDS))
            writer.writeheader()
            writer.writerows(entries)


class XmlHandler:
    """XML layout: <config><entry section="s" key="k">value</entry></config>"""

    def iter_entries(self, path: Path) -> Iterator[ConfigEntry]:
        try:
            # iterparse reads the file incrementally instead of building the whole tree
            root: ET.Element | None = None
            for event, element in ET.iterparse(path, events=("start", "end")):
                if root is None:
                    root = element  # the first element seen is the root
                if event != "end" or element.tag != "entry":
                    continue
                yield validate_entry(
                    {
                        "section": element.get("section", ""),
                        "key": element.get("key", ""),
                        "value": element.text or "",
                    }
                )
                root.clear()  # drop processed children so memory stays flat
        except ET.ParseError as err:
            raise ConfigParseError(f"Invalid XML in {path}: {err}") from err

    def write(self, entries: Iterable[ConfigEntry], path: Path) -> None:
        root = ET.Element("config")
        for entry in entries:
            child = ET.SubElement(
                root, "entry", section=entry["section"], key=entry["key"]
            )
            child.text = entry["value"]
        ET.indent(root)
        ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
