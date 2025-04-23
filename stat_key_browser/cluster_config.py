"""
Connects to a PowerScale cluster and dynamically loads the correct OneFS API bindings
based on the OneFS version. Uses isilon_sdk (modern SDK as of OneFS 9.4+).
"""

import logging
import importlib
from typing import Any, Tuple

import isilon_sdk
from isilon_sdk.rest import ApiException as RawApiException

class ApiException(Exception):
    """Raised when API call or SDK import fails."""
    pass


def get_base_release(cluster_ip: str, username: str, password: str) -> Tuple[str, str]:
    """
    Use isilon_sdk base client to retrieve the OneFS version.
    Returns:
      - release: '9.9.0.0'
      - module name: 'v9_9_0'
    """
    config = isilon_sdk.Configuration()
    config.host = f"https://{cluster_ip}:8080"
    config.username = username
    config.password = password
    config.verify_ssl = False

    client = isilon_sdk.ApiClient(config)
    cluster_api = isilon_sdk.ClusterApi(client)

    try:
        info = cluster_api.get_cluster_config().to_dict()
        version_str = info["onefs_version"]["release"]
        version_mod = "v" + "_".join(version_str.split(".")[:3])
        return version_str, version_mod
    except RawApiException as e:
        raise ApiException(f"Failed to get cluster version: {e}")
    except KeyError:
        raise ApiException("Expected key 'onefs_version.release' not found in API response.")


def load_versioned_sdk_module(version_module: str):
    """
    Dynamically import the isilon_sdk.<version_module>.
    Example: 'v9_9_0' → isilon_sdk.v9_9_0
    """
    try:
        return importlib.import_module(f"isilon_sdk.{version_module}")
    except ImportError as e:
        raise ApiException(
            f"Could not import isilon_sdk.{version_module}. Is the SDK installed?"
        ) from e
