"""
Query the PowerScale cluster for statistics keys.

Uses the PAPI (Platform API) via the OneFS Python SDK to download all available stat keys.
Then it:
- Converts them into a dict keyed by stat name
- Squashes any numeric suffixes to a placeholder `.N` (e.g. node.net.iface.1 → node.net.iface.N)
- Converts abbreviated field values to full names
"""

import logging
import re
from typing import Dict, List, Any

from isilon_sdk.v9_10_0 import Configuration, ApiClient, StatisticsApi


class KeyCollector:
    def __init__(self, cluster_ip: str, username: str, password: str):
        # Store credentials for use in API connection
        self.cluster_ip = cluster_ip
        self.username = username
        self.password = password

        # Set up SDK Configuration object
        config = Configuration()
        config.host = f"https://{cluster_ip}:8080"
        config.username = username
        config.password = password
        config.verify_ssl = False  # Disable cert check for internal use

        # Create an API client using this configuration
        self.api_client = ApiClient(config)

        # Instantiate the Statistics API to query stat keys
        self.statistics_api = StatisticsApi(self.api_client)

        logging.info(f"Using static SDK version v9_10_0")

    def get_tagged_squashed_dict(self) -> Dict[str, Any]:
        """
        Primary public method: fetches, normalizes, and processes all stat keys.
        Returns a dictionary mapping key names to metadata dicts.
        """
        key_dict = self._get_key_dict()
        key_dict = self._squash_keys(key_dict)
        self._deabbreviate(key_dict)
        return key_dict

    def _get_key_dict(self) -> Dict[str, Any]:
        """
        Converts the raw list of stat entries into a dictionary where the key is the stat name.
        """
        key_list = self._get_key_list()
        return {entry["key"]: entry for entry in key_list}

    def _get_key_list(self) -> List[Dict[str, Any]]:
        """
        Calls the PowerScale cluster to retrieve a list of available statistics keys.
        """
        logging.debug(f"Querying {self.cluster_ip} for statistics keys")
        return self.statistics_api.get_statistics_keys().to_dict()["keys"]

    def _squash_keys(self, key_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes keys that are numerically indexed (like node.net.iface.0).
        Rewrites them as node.net.iface.N so that similar keys don't appear as separate entries.
        """
        indexed_keys = [k for k in key_dict if re.match(r".*\.[0-9]+$", k)]
        squashed_keys = {}

        for key in indexed_keys:
            base = self._basename(key)              # e.g. iface.1 → iface
            entry = key_dict.pop(key)               # Remove original key
            squashed_name = f"{base}.N"             # Replace index with 'N'

            # Store under squashed name instead
            squashed_keys[squashed_name] = entry

            # Update the internal "key" value and description too
            if "key" in entry:
                entry["key"] = squashed_name
            if "description" in entry:
                entry["description"] = self._squash_description(entry["description"])

        key_dict.update(squashed_keys)
        return key_dict

    def _deabbreviate(self, key_dict: Dict[str, Any]) -> None:
        """
        Replaces known abbreviated metadata with full names (e.g. avg → average).
        This improves readability in the frontend UI.
        """
        mappings = {
            "aggregation_type": {
                "avg": "average",
                "max": "maximum",
                "min": "minimum"
            }
        }

        for key in key_dict.values():
            for field, abbrevs in mappings.items():
                if field in key and key[field] in abbrevs:
                    key[field] = abbrevs[key[field]]

    def _basename(self, key: str) -> str:
        """
        Returns the part of the key path *before* the numeric index.
        Example: 'node.iface.1' → 'node.iface'
        """
        return ".".join(key.split(".")[:-1])

    def _squash_description(self, desc: str) -> str:
        """
        Tries to make the key's description match the squashed key name.
        It replaces numeric values or phrases like 'index 3' → 'index N'.
        If no known pattern matches, logs a warning and leaves it unchanged.
        """
        if re.search(r"[0-9]+$", desc):
            return re.sub(r"[0-9]+$", "N", desc)
        if re.search(r"index [0-9]+", desc):
            return re.sub(r"index [0-9]+", "index N", desc)
        if re.search(r"number [0-9]+", desc):
            return re.sub(r"number [0-9]+", "number N", desc)

        # No matching replacement found — log it
        logging.warning(f"Did not know how to squash description: {desc}")
        return desc
