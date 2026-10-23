import inspect
from pathlib import Path

import pytest

from configuration_file_manager.exceptions import (
    ConfigParseError,
    ConfigValidationError,
)
from configuration_file_manager.handlers import CsvHandler, JsonHandler, XmlHandler
from configuration_file_manager.schema import ConfigEntry, validate_entry

EXPECTED_FIRST = {"section": "database", "key": "host", "value": "localhost"}


@pytest.mark.parametrize(
    ("handler", "filename"),
    [(JsonHandler(), "app.json"), (CsvHandler(), "app.csv"), (XmlHandler(), "app.xml")],
)
def test_each_format_reads_four_entries(
    handler, filename: str, sample_dir: Path
) -> None:
    entries = list(handler.iter_entries(sample_dir / filename))
    assert len(entries) == 4
    assert entries[0] == EXPECTED_FIRST


@pytest.mark.parametrize(
    ("handler", "suffix"),
    [(JsonHandler(), ".json"), (CsvHandler(), ".csv"), (XmlHandler(), ".xml")],
)
def test_each_format_round_trips(handler, suffix: str, tmp_path: Path) -> None:
    entries = [
        ConfigEntry(section="a", key="x", value="1"),
        ConfigEntry(section="b", key="y", value="two words"),
    ]
    path = tmp_path / f"out{suffix}"
    handler.write(entries, path)
    assert list(handler.iter_entries(path)) == entries


def test_iter_entries_is_a_generator(sample_dir: Path) -> None:
    gen = CsvHandler().iter_entries(sample_dir / "app.csv")
    assert inspect.isgenerator(gen)
    assert next(gen) == EXPECTED_FIRST


def test_invalid_json_raises_parse_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigParseError):
        list(JsonHandler().iter_entries(bad))


def test_invalid_xml_raises_parse_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.xml"
    bad.write_text("<config><entry>", encoding="utf-8")
    with pytest.raises(ConfigParseError):
        list(XmlHandler().iter_entries(bad))


def test_csv_wrong_header_raises_parse_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("name,val\na,1\n", encoding="utf-8")
    with pytest.raises(ConfigParseError):
        list(CsvHandler().iter_entries(bad))


def test_missing_field_raises_validation_error(sample_dir: Path) -> None:
    with pytest.raises(ConfigValidationError):
        list(JsonHandler().iter_entries(sample_dir / "invalid.json"))


@pytest.mark.parametrize(
    "raw",
    ["text", {"section": "", "key": "k", "value": "v"}, {"key": "k", "value": "v"}],
)
def test_validate_entry_rejects_bad_input(raw: object) -> None:
    with pytest.raises(ConfigValidationError):
        validate_entry(raw)


def test_validate_entry_strips_whitespace() -> None:
    assert validate_entry({"section": " a ", "key": " k", "value": 5}) == {
        "section": "a",
        "key": "k",
        "value": "5",
    }
