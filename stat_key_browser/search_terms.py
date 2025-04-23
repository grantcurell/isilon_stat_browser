"""
Generate a set of search terms from a stat key's fields.

Fields used: key name, description, tags, and extra attributes.
"""

from typing import Dict, List, Any

KEY = "key"
DESCRIPTION = "description"
TAGS = "tags"
XTRA_ATTRS = "xtra_attrs"
SEARCH_TERMS = "search_terms"


def list_search_terms(key: Dict[str, Any]) -> List[str]:
    """
    Given a single key dict, extract relevant search terms from:
    - key name (split by dot)
    - description (split by space)
    - tags (lowercased)
    - extra attributes (split by space)
    Returns a deduplicated list of lowercase search terms.
    """
    terms: List[str] = []

    if KEY in key:
        key_str = key[KEY].lower()
        terms.extend(key_str.split("."))
        terms.append(key_str)

    if DESCRIPTION in key:
        terms.extend(key[DESCRIPTION].lower().split())

    if TAGS in key:
        terms.extend(tag.lower() for tag in key[TAGS])

    if XTRA_ATTRS in key:
        for val in key[XTRA_ATTRS].values():
            terms.extend(val.lower().split())

    return sorted(set(terms))


def add_to_dict(key_dict: Dict[str, Dict[str, Any]]) -> None:
    """
    For each key in the key_dict, populate a 'search_terms' field
    with a list of useful terms for UI search.
    """
    for key in key_dict.values():
        key[SEARCH_TERMS] = list_search_terms(key)
