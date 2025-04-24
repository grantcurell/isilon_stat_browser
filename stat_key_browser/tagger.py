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

import stat_key_browser  # Used only to get the base path for relative access to data files

# Name of the JSON file storing tag rules
KEY_TAG_DEFS_FILENAME = "key_tags.json"

# Key under which custom (non-tag) attributes are stored in a stat key’s metadata
EXTRA_ATTRS = "xtra_attrs"


class TagDefinitionError(Exception):
    """Custom exception thrown if the tag definitions file cannot be read."""
    pass


class Tagger:
    """
    Tagger reads tag definitions from a JSON file and applies those tags to
    keys in a stat dictionary.

    Tags and attributes can be applied either:
      - By exact stat key match (`keys`)
      - By regex match (`re-keys`)
    """

    def __init__(self, defs: List[Dict[str, Any]] = None):
        """
        If tag definitions are not passed explicitly, load them from disk.

        :param defs: Optional preloaded list of tag definitions (mainly for testing)
        """
        if defs is None:
            def_path = self.get_defs_path()
            try:
                # Read the tag definitions from the expected file
                with def_path.open("r", encoding="utf-8") as def_file:
                    defs = json.load(def_file)
            except OSError as err:
                logging.error(f"Unable to open tag definitions at {def_path}: {err}")
                logging.error("Try running 'make tags' to create the tag file")
                raise TagDefinitionError(f"Could not load tag definitions from {def_path}") from err
        self.tag_defs = defs

    def get_defs_path(self) -> Path:
        """
        Locate the path to the key tag definition file relative to the module.

        :return: Full path to the `key_tags.json` file under stat_key_browser/data
        """
        basedir = Path(stat_key_browser.__path__[0])
        defs_path = basedir / "data" / KEY_TAG_DEFS_FILENAME
        logging.debug(f"Expecting key tag definitions at {defs_path}")
        return defs_path

    def tag_list(self) -> List[str]:
        """
        Return a list of all tags defined across all definitions.
        Useful for building tag filters in the frontend.

        :return: Alphabetically sorted list of all tags.
        """
        tags = {tag for defin in self.tag_defs for tag in defin.get("tags", [])}
        return sorted(tags)

    def tag_keys(self, key_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply tag definitions to the stat key dictionary.

        For each tag definition:
        - If a stat key matches `keys`, apply its tags
        - If a stat key matches `re-keys` (regex), apply its tags
        - Apply any additional attributes (like 'description', 'source', etc.)

        :param key_dict: Raw stat key dictionary from the cluster
        :return: Updated dictionary with applied tags and extra attributes
        """
        for defin in self.tag_defs:
            extra_attrs = self._get_extra_attrs(defin)

            # Match stat keys exactly
            for key in defin.get("keys", []):
                if key in key_dict:
                    self._add_tags(key_dict[key], defin["tags"])
                    self._add_extra_attrs(key_dict[key], extra_attrs)

            # Match stat keys using regex
            for re_key in defin.get("re-keys", []):
                pattern = re.compile(re_key)
                for key, data in key_dict.items():
                    if pattern.search(key):
                        self._add_tags(data, defin["tags"])
                        self._add_extra_attrs(data, extra_attrs)

        # Ensure tag lists contain no duplicates and are sorted
        return self._dedupe_tag_lists(key_dict)

    def _get_extra_attrs(self, defin: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract non-standard attributes from a tag definition stanza.

        For example:
        :::Extra Info
        Some message

        will be parsed into:
        { "Extra Info": ["Some message"] }

        :raises ValueError if any attribute list has more than one item
        """
        extra = {k: v for k, v in defin.items() if k not in {"keys", "re-keys", "tags"}}
        for attr, val in extra.items():
            if len(val) != 1:
                raise ValueError(f"Extra attribute '{attr}' must have a single value, got: {val}")
        return extra

    def _add_tags(self, key: Dict[str, Any], tags: List[str]) -> None:
        """
        Append tags to a given stat key's metadata.

        :param key: The individual stat key entry (a dict)
        :param tags: Tags to append
        """
        key.setdefault("tags", []).extend(tags)

    def _add_extra_attrs(self, key: Dict[str, Any], extra_attrs: Dict[str, List[str]]) -> None:
        """
        Add additional metadata to the key under `xtra_attrs`.

        Each value is converted from list-of-one to a single string.
        """
        key.setdefault(EXTRA_ATTRS, {})
        for attr_name, val in extra_attrs.items():
            key[EXTRA_ATTRS][attr_name] = "\n".join(val)

    def _dedupe_tag_lists(self, key_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deduplicate and sort the tag lists on all stat keys.
        Tags may have been applied multiple times from different definitions.
        """
        for data in key_dict.values():
            if "tags" in data:
                data["tags"] = sorted(set(data["tags"]))
        return key_dict
