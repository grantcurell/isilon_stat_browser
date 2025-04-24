"""
Connects to a PowerScale cluster using a fixed OneFS SDK version.
"""

from typing import Tuple
from isilon_sdk.v9_10_0 import Configuration, ApiClient, ClusterApi
from isilon_sdk.v9_10_0.rest import ApiException as RawApiException


class ApiException(Exception):
    """Raised when API call or SDK import fails."""
    pass


def get_base_release(cluster_ip: str, username: str, password: str) -> Tuple[str, str]:
    """
    Returns:
      - release: e.g., '9.10.0.0'
      - version_mod: always 'v9_10_0'
    """
    config = Configuration()
    config.host = f"https://{cluster_ip}:8080"
    config.username = username
    config.password = password
    config.verify_ssl = False

    client = ApiClient(config)
    cluster_api = ClusterApi(client)

    try:
        info = cluster_api.get_cluster_config().to_dict()
        version_str = info["onefs_version"]["release"]
        return version_str, "v9_10_0"
    except RawApiException as e:
        raise ApiException(f"Failed to get cluster version: {e}")
    except KeyError:
        raise ApiException("Expected key 'onefs_version.release' not found in API response.")
