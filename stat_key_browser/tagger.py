"""
Provide access to the tag definitions and tagging utilities.

Reads and parses a JSON tag definition file.
Tags keys in a dictionary based on the definitions.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

import stat_key_browser

KEY_TAG_DEFS_FILENAME = "key_tags.json"
EXTRA_ATTRS = "xtra_attrs"


class TagDefinitionError(Exception):
    """Custom exception for tag definition loading errors."""
    pass


class Tagger:
    def __init__(self, defs: List[Dict[str, Any]] = None):
        if defs is None:
            def_path = self.get_defs_path()
            try:
                with def_path.open("r", encoding="utf-8") as def_file:
                    defs = json.load(def_file)
            except OSError as err:
                logging.error(f"Unable to open tag definitions at {def_path}: {err}")
                logging.error("Try running 'make tags' to create the tag file")
                raise TagDefinitionError(f"Could not load tag definitions from {def_path}") from err
        self.tag_defs = defs

    def get_defs_path(self) -> Path:
        """Return path to tag definitions file."""
        basedir = Path(stat_key_browser.__path__[0])
        defs_path = basedir / "data" / KEY_TAG_DEFS_FILENAME
        logging.debug(f"Expecting key tag definitions at {defs_path}")
        return defs_path

    def tag_list(self) -> List[str]:
        """Return a sorted list of all tags from all definitions."""
        tags = {tag for defin in self.tag_defs for tag in defin.get("tags", [])}
        return sorted(tags)

    def tag_keys(self, key_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply tag definitions to keys in the dictionary."""
        for defin in self.tag_defs:
            extra_attrs = self._get_extra_attrs(defin)
            for key in defin.get("keys", []):
                if key in key_dict:
                    self._add_tags(key_dict[key], defin["tags"])
                    self._add_extra_attrs(key_dict[key], extra_attrs)

            for re_key in defin.get("re-keys", []):
                pattern = re.compile(re_key)
                for key, data in key_dict.items():
                    if pattern.search(key):
                        self._add_tags(data, defin["tags"])
                        self._add_extra_attrs(data, extra_attrs)

        return self._dedupe_tag_lists(key_dict)

    def _get_extra_attrs(self, defin: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extract arbitrary key/value attributes outside of known fields."""
        extra = {k: v for k, v in defin.items() if k not in {"keys", "re-keys", "tags"}}
        for attr, val in extra.items():
            if len(val) != 1:
                raise ValueError(f"Extra attribute '{attr}' must have a single value, got: {val}")
        return extra

    def _add_tags(self, key: Dict[str, Any], tags: List[str]) -> None:
        key.setdefault("tags", []).extend(tags)

    def _add_extra_attrs(self, key: Dict[str, Any], extra_attrs: Dict[str, List[str]]) -> None:
        key.setdefault(EXTRA_ATTRS, {})
        for attr_name, val in extra_attrs.items():
            key[EXTRA_ATTRS][attr_name] = "\n".join(val)

    def _dedupe_tag_lists(self, key_dict: Dict[str, Any]) -> Dict[str, Any]:
        for data in key_dict.values():
            if "tags" in data:
                data["tags"] = sorted(set(data["tags"]))
        return key_dict
