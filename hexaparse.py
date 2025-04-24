#!/usr/bin/env python3
"""
Parse a .hexa key/list-of-values doc into JSON files.

Each list item is a dict. The output files are:
- stat_key_browser/data/key_tags.json
- stat_key_browser/data/key_cats.json
"""

import sys
import json
import re
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%dT%H:%M:%S',
                    format='%(asctime)s [%(levelname)s] %(message)s')


def is_new_block(line):
    return re.match(r'^::::::$', line.strip()) is not None


def is_key(line):
    return re.match(r'^:::[^:]', line.strip()) is not None


def is_comment(line):
    return line.strip().startswith("#")


def hexakey(line):
    return line.strip()[3:].strip()


def parse_hexa_file(path: Path):
    """
    Parse a hexa-formatted file into a list of dictionaries.
    Each dictionary represents a block.
    """
    logging.info(f"Parsing {path}")
    blocks = []
    block = {}
    key = None
    values = []

    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or is_comment(line):
                continue
            elif is_new_block(line):
                if key:
                    block[key] = values
                if block:
                    blocks.append(block)
                block = {}
                key = None
                values = []
            elif is_key(line):
                if key:
                    block[key] = values
                key = hexakey(line)
                values = []
            else:
                if key is None:
                    raise ValueError(f"Missing key before value on line {lineno}")
                values.append(line)

    # Final flush
    if key:
        block[key] = values
    if block:
        blocks.append(block)

    return blocks


def write_json(data, path: Path):
    """Write the given data to a file with UTF-8 (no BOM)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logging.info(f"Wrote {len(data)} blocks to {path}")


def main():
    base_dir = Path(__file__).parent
    data_dir = base_dir / "stat_key_browser" / "data"

    tag_file = data_dir / "key_tags.hexa"
    cat_file = data_dir / "key_cats.hexa"

    tag_output = data_dir / "key_tags.json"
    cat_output = data_dir / "key_cats.json"

    tag_data = parse_hexa_file(tag_file)
    cat_data = parse_hexa_file(cat_file)

    write_json(tag_data, tag_output)
    write_json(cat_data, cat_output)


if __name__ == "__main__":
    main()
