"""
Provide access to category definitions and tagging utilities.

Parses a JSON category definition file and applies category structure to a key_dict.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import stat_key_browser

CAT_TAG_DEFS_FILENAME = "key_cats.json"
DEFAULT_CATEGORY = "Uncategorized"
DEFAULT_CAT_DESC = "Statistics that have not been assigned a category."


class CategoryDefinitionError(Exception):
    """Raised when the category definitions are malformed or missing."""
    pass


class Categorizer:
    def __init__(self, defs: Optional[List[Dict[str, Any]]] = None):
        self.default_category = DEFAULT_CATEGORY
        if defs is None:
            def_path = self._get_defs_path()
            try:
                with def_path.open("r", encoding="utf-8") as f:
                    defs = json.load(f)
            except OSError as e:
                logging.error(f"Unable to open {def_path}: {e}")
                raise CategoryDefinitionError(f"Could not load category definitions from {def_path}") from e
        self.validate_defs(defs)
        self.cat_defs = self._flatten_uni_attrs(defs)

    def _get_defs_path(self) -> Path:
        basedir = Path(stat_key_browser.__path__[0])
        return basedir / "data" / CAT_TAG_DEFS_FILENAME

    def validate_defs(self, defins: List[Dict[str, Any]]) -> None:
        valid_attrs = {"super", "sub", "subsub", "keys", "re-keys", "category description"}
        for defin in defins:
            for key in defin:
                if key not in valid_attrs:
                    raise ValueError(f'Invalid attribute "{key}" in category definition: {defin}')
            if "super" not in defin or not isinstance(defin["super"], list) or len(defin["super"]) != 1:
                raise ValueError(f'Missing or invalid "super" category in: {defin}')
            if "sub" in defin and len(defin["sub"]) != 1:
                raise ValueError(f'Multiple "sub" categories defined in: {defin}')
            if "subsub" in defin and len(defin["subsub"]) != 1:
                raise ValueError(f'Multiple "subsub" categories defined in: {defin}')

    def _flatten_uni_attrs(self, defins: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Flatten any list-based fields into strings."""
        for defin in defins:
            defin["super"] = defin["super"][0]
            if "sub" in defin:
                defin["sub"] = defin["sub"][0]
            if "subsub" in defin:
                defin["subsub"] = defin["subsub"][0]
            if "category description" in defin:
                defin["category description"] = defin["category description"][0]
        return defins

    def get_categories_list(self) -> List[str]:
        """Return a list of all category names (super + sub)."""
        cats = set()
        for defin in self.cat_defs:
            cats.add(defin["super"])
            if "sub" in defin:
                cats.add(defin["sub"])
        return sorted(cats)

    def categorize(self, key_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply category data to key_dict and return a full category tree."""
        key_dict = self._apply_categories(key_dict)
        cat_dict = self._build_category_tree()
        cat_dict = self._insert_keys(key_dict, cat_dict)
        return cat_dict

    def _build_category_tree(self) -> Dict[str, Any]:
        cat_dict = {}

        for defin in self.cat_defs:
            supercat = defin["super"]
            cat_dict.setdefault(supercat, {
                "categories": {},
                "keys": [],
                "description": defin.get("category description", "")
            })

            if "sub" in defin:
                subcat = defin["sub"]
                cat_dict[supercat]["categories"].setdefault(subcat, {
                    "categories": {},
                    "keys": [],
                    "description": defin.get("category description", "")
                })

                if "subsub" in defin:
                    subsubcat = defin["subsub"]
                    cat_dict[supercat]["categories"][subcat]["categories"].setdefault(subsubcat, {
                        "categories": {},
                        "keys": [],
                        "description": defin.get("category description", "")
                    })

        cat_dict[DEFAULT_CATEGORY] = {
            "categories": {},
            "keys": [],
            "description": DEFAULT_CAT_DESC
        }

        return cat_dict

    def _insert_keys(self, key_dict: Dict[str, Any], cat_dict: Dict[str, Any]) -> Dict[str, Any]:
        for key, data in key_dict.items():
            supercat = data.get("super", DEFAULT_CATEGORY)
            subcat = data.get("sub")
            subsubcat = data.get("subsub")

            if subsubcat:
                cat_dict[supercat]["categories"][subcat]["categories"][subsubcat]["keys"].append(key)
            elif subcat:
                cat_dict[supercat]["categories"][subcat]["keys"].append(key)
            else:
                cat_dict[supercat]["keys"].append(key)
        return cat_dict

    def _match_key_to_cat(self, key: str) -> Tuple[str, Optional[str], Optional[str]]:
        for defin in self.cat_defs:
            if "keys" in defin and key in defin["keys"]:
                return defin["super"], defin.get("sub"), defin.get("subsub")

            for re_key in defin.get("re-keys", []):
                if re.search(re_key, key):
                    return defin["super"], defin.get("sub"), defin.get("subsub")

        return DEFAULT_CATEGORY, None, None

    def _apply_categories(self, key_dict: Dict[str, Any]) -> Dict[str, Any]:
        for key, data in key_dict.items():
            supercat, subcat, subsubcat = self._match_key_to_cat(key)
            data["super"] = supercat
            data["sub"] = subcat
            data["subsub"] = subsubcat
        return key_dict
