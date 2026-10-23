from pathlib import Path

import pytest
from configuration_file_manager.cli import main

from configuration_file_manager import manager
from configuration_file_manager.exceptions import (
    ConfigNotFoundError,
    ConfigValidationError,
    UnsupportedFormatError,
)


def test_discover_finds_only_supported_files(sample_dir: Path) -> None:
    (sample_dir / "notes.txt").write_text("x", encoding="utf-8")
    names = [p.name for p in manager.discover(sample_dir)]
    assert names == ["app.csv", "app.json", "app.xml", "invalid.json"]


def test_discover_recurses_into_subfolders(sample_dir: Path) -> None:
    sub = sample_dir / "nested"
    sub.mkdir()
    (sub / "deep.json").write_text('{"entries": []}', encoding="utf-8")
    assert "deep.json" in [p.name for p in manager.discover(sample_dir)]
    assert "deep.json" not in [
        p.name for p in manager.discover(sample_dir, recursive=False)
    ]


def test_discover_missing_folder_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigNotFoundError):
        manager.discover(tmp_path / "nope")


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigNotFoundError):
        manager.load_config(tmp_path / "missing.json")


def test_unsupported_extension_raises(tmp_path: Path) -> None:
    path = tmp_path / "a.yaml"
    path.write_text("x: 1", encoding="utf-8")
    with pytest.raises(UnsupportedFormatError):
        manager.load_config(path)


def test_validate_counts_entries(sample_dir: Path) -> None:
    assert manager.validate_config(sample_dir / "app.json") == 4


def test_validate_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "dup.csv"
    path.write_text("section,key,value\na,x,1\na,x,2\n", encoding="utf-8")
    with pytest.raises(ConfigValidationError):
        manager.validate_config(path)


@pytest.mark.parametrize("target", ["out.csv", "out.xml", "out.json"])
def test_convert_json_to_every_format_keeps_content(
    target: str, sample_dir: Path
) -> None:
    out = sample_dir / target
    assert manager.convert(sample_dir / "app.json", out) == 4
    assert manager.load_config(out) == manager.load_config(sample_dir / "app.json")


def test_convert_filters_empty_values_and_lowercases(tmp_path: Path) -> None:
    src = tmp_path / "in.csv"
    src.write_text("section,key,value\nDB,Host,x\nDB,Empty,\n", encoding="utf-8")
    out = tmp_path / "out.json"
    assert manager.convert(src, out) == 1
    assert manager.load_config(out) == [{"section": "db", "key": "host", "value": "x"}]


def test_convert_backs_up_existing_destination(sample_dir: Path) -> None:
    manager.convert(sample_dir / "app.json", sample_dir / "app.csv")
    assert len(list(sample_dir.glob("app.csv.*.bak"))) == 1


def test_failed_convert_leaves_destination_untouched(sample_dir: Path) -> None:
    dest = sample_dir / "app.csv"
    original = dest.read_text(encoding="utf-8")
    with pytest.raises(ConfigValidationError):
        manager.convert(sample_dir / "invalid.json", dest)
    assert dest.read_text(encoding="utf-8") == original
    assert not list(sample_dir.glob("*.tmp"))


def test_transaction_rolls_back_on_error(tmp_path: Path) -> None:
    target = tmp_path / "t.json"
    target.write_text("original", encoding="utf-8")
    with pytest.raises(RuntimeError), manager.config_transaction(target) as temp:
        temp.write_text("new", encoding="utf-8")
        raise RuntimeError("boom")
    assert target.read_text(encoding="utf-8") == "original"
    assert not (tmp_path / "t.json.tmp").exists()


def test_transaction_commits_on_success(tmp_path: Path) -> None:
    target = tmp_path / "t.json"
    with manager.config_transaction(target) as temp:
        temp.write_text("new", encoding="utf-8")
    assert target.read_text(encoding="utf-8") == "new"


def test_cli_validate_ok_and_error(sample_dir: Path, capsys) -> None:
    assert main(["validate", str(sample_dir / "app.xml")]) == 0
    assert "4 entries" in capsys.readouterr().out
    assert main(["validate", str(sample_dir / "invalid.json")]) == 1
    assert "Error:" in capsys.readouterr().err


def test_cli_convert_and_list(sample_dir: Path, capsys) -> None:
    assert (
        main(["convert", str(sample_dir / "app.json"), str(sample_dir / "x.xml")]) == 0
    )
    assert main(["list", str(sample_dir)]) == 0
    assert "x.xml" in capsys.readouterr().out
