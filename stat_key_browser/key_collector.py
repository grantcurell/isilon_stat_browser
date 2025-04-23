"""
Query the PowerScale cluster for statistics keys.

Uses PAPI to download all keys, converts them into a dict,
squashes indexed keys (like a.b.c.1 -> a.b.c.N), and de-abbreviates values.
"""

import logging
import re
from typing import Dict, List, Any

try:
    import isi_sdk_7_2 as isi_sdk
except ImportError:
    try:
        import isi_sdk
    except ImportError as e:
        logging.critical("Unable to import isi_sdk_7_2 or isi_sdk. Isilon SDK must be installed.")
        raise ImportError(
            "Missing Isilon SDK. Install from: https://github.com/isilon"
        ) from e


class KeyCollector:
    def __init__(self, cluster_ip: str, username: str, password: str):
        self.cluster_ip = cluster_ip
        self.username = username
        self.password = password

    def get_tagged_squashed_dict(self) -> Dict[str, Any]:
        """Return fully prepared stat key dictionary."""
        key_dict = self._get_key_dict()
        key_dict = self._squash_keys(key_dict)
        self._deabbreviate(key_dict)
        return key_dict

    def _get_key_dict(self) -> Dict[str, Any]:
        key_list = self._get_key_list()
        return {entry["key"]: entry for entry in key_list}

    def _get_key_list(self) -> List[Dict[str, Any]]:
        isi_sdk.configuration.username = self.username
        isi_sdk.configuration.password = self.password
        isi_sdk.configuration.verify_ssl = False  # This is insecure in prod

        host = f"https://{self.cluster_ip}:8080"
        papi = isi_sdk.ApiClient(host)
        statistics = isi_sdk.StatisticsApi(papi)

        logging.debug(f"Querying {self.cluster_ip} for statistics keys")
        return statistics.get_statistics_keys().to_dict()["keys"]

    def _squash_keys(self, key_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Squash indexed keys like a.b.1 → a.b.N."""
        indexed_keys = [k for k in key_dict if re.match(r".*\.[0-9]+$", k)]
        squashed_keys = {}

        for key in indexed_keys:
            base = self._basename(key)
            entry = key_dict.pop(key)
            squashed_name = f"{base}.N"
            squashed_keys[squashed_name] = entry

            if "key" in entry:
                entry["key"] = squashed_name
            if "description" in entry:
                entry["description"] = self._squash_description(entry["description"])

        key_dict.update(squashed_keys)
        return key_dict

    def _deabbreviate(self, key_dict: Dict[str, Any]) -> None:
        """Replace known abbreviations with human-friendly text."""
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
        """Strip the final index from dotted key name."""
        return ".".join(key.split(".")[:-1])

    def _squash_description(self, desc: str) -> str:
        if re.search(r"[0-9]+$", desc):
            return re.sub(r"[0-9]+$", "N", desc)
        if re.search(r"index [0-9]+", desc):
            return re.sub(r"index [0-9]+", "index N", desc)
        if re.search(r"number [0-9]+", desc):
            return re.sub(r"number [0-9]+", "number N", desc)
        logging.warning(f"Did not know how to squash description: {desc}")
        return desc
