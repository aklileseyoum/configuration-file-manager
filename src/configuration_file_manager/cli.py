"""Command-line interface: list / validate / convert."""

import argparse
import logging
import sys
from pathlib import Path

from configuration_file_manager import manager
from configuration_file_manager.exceptions import ConfigError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="config-manager")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="find config files in a folder")
    p_list.add_argument("directory", type=Path)

    p_val = sub.add_parser("validate", help="validate a config file")
    p_val.add_argument("path", type=Path)

    p_conv = sub.add_parser("convert", help="convert between formats")
    p_conv.add_argument("source", type=Path)
    p_conv.add_argument("destination", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args(argv)
    try:
        if args.command == "list":
            for path in manager.discover(args.directory):
                print(path)
        elif args.command == "validate":
            count = manager.validate_config(args.path)
            print(f"OK: {count} entries are valid in {args.path}")
        else:
            count = manager.convert(args.source, args.destination)
            print(f"Converted {count} entries to {args.destination}")
    except ConfigError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
