"""
Generate key and category name mappings to HTML-safe IDs.
"""

import hashlib
from typing import Dict, Optional


def _convert_to_id(name: str) -> str:
    """Convert a name to an MD5-based HTML-safe ID."""
    return hashlib.md5(name.encode("utf-8")).hexdigest()


def cat_join(*args: Optional[str]) -> str:
    """Join category components into a unified string."""
    return "-".join(str(a) for a in args if a is not None)


def cat_id(category: str) -> str:
    """Prefix the MD5 of the category string for DOM use."""
    return f"cat_{_convert_to_id(category)}"


def key_ids(key_dict: Dict[str, dict], prefix: str = "key_") -> Dict[str, str]:
    """Map each key name to a unique HTML ID."""
    return {key_name: f"{prefix}{_convert_to_id(key_name)}" for key_name in key_dict}


def category_ids(key_dict: Dict[str, dict]) -> Dict[str, str]:
    """
    Generate HTML-safe IDs for each unique category path (super, sub, subsub).
    """
    mapping: Dict[str, str] = {}
    for value in key_dict.values():
        supercat = value.get("super")
        subcat = value.get("sub")
        subsubcat = value.get("subsub")

        if supercat:
            path = cat_join(supercat)
            mapping.setdefault(path, cat_id(path))
        if supercat and subcat:
            path = cat_join(supercat, subcat)
            mapping.setdefault(path, cat_id(path))
        if supercat and subcat and subsubcat:
            path = cat_join(supercat, subcat, subsubcat)
            mapping.setdefault(path, cat_id(path))
    return mapping
