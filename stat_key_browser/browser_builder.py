"""Manage the creation of the key browser UI."""

import json
import logging
from pathlib import Path

from jinja2 import Environment, PackageLoader  # For HTML template rendering

# Local project imports — these provide various stages of the stat key processing pipeline
import stat_key_browser.cluster_config as cluster_config
import stat_key_browser.search_terms as search_terms
from stat_key_browser.tagger import Tagger
from stat_key_browser.categorizer import Categorizer
import stat_key_browser.key_collector as key_collector
import stat_key_browser.mapper as mapper
from stat_key_browser.cluster_config import ApiException

# Define constant paths and filenames for output
OUTPUT_DIR = Path("web_app")
JS_DIR = OUTPUT_DIR / "js"
HTML_FNAME = "index.html"
JSKEYS_FNAME = "keys.js"
UNKNOWN_RELEASE = "unknown"


class BrowserBuilder:
    """
    Generates the complete web app UI for browsing PowerScale stat keys.

    - Connects to a OneFS cluster to retrieve raw stat keys via PAPI
    - Normalizes, tags, and categorizes those keys
    - Outputs:
        * keys.js – contains all cluster key metadata
        * index.html – a stat browser frontend rendered from a Jinja2 template
    """

    def __init__(self, cluster_ip: str, username: str, password: str, store_ip: bool):
        """
        :param cluster_ip: IP address of the cluster
        :param username: cluster login name
        :param password: cluster login password
        :param store_ip: whether to include the cluster IP in the frontend output (optional)
        """
        self.cluster_ip = cluster_ip
        self.username = username
        self.password = password
        self.store_ip = store_ip

    def _get_cluster_info(self) -> dict:
        """
        Retrieve OneFS version info from the cluster to embed in UI metadata.
        Falls back to 'unknown' if connection or version detection fails.
        """
        try:
            release, _ = cluster_config.get_base_release(self.cluster_ip, self.username, self.password)
        except ApiException:
            logging.warning("Unable to determine OneFS version via SDK")
            release = UNKNOWN_RELEASE

        return {
            "release": release,
            "host": self.cluster_ip if self.store_ip else None,
        }

    def _transform_key_dict(self, key_dict: dict) -> dict:
        """
        Apply post-processing to stat keys:
        - Tag each key with relevant labels
        - Add searchable terms
        """
        tagger = Tagger()
        key_dict = tagger.tag_keys(key_dict)

        search_terms.add_to_dict(key_dict)
        return key_dict

    def _build_dataset(self, key_dict: dict) -> dict:
        """
        Bundle the final structured data:
        - Categorized keys
        - Tagged metadata
        - Mappings from keys to IDs (for use in frontend)
        - Cluster information
        """
        categorizer = Categorizer()
        categories = categorizer.categorize(key_dict)

        tagger = Tagger()
        tags = tagger.tag_list()

        mappings = {
            "keys": mapper.key_ids(key_dict),
            "categories": mapper.category_ids(key_dict),
        }

        return {
            "categories": categories,
            "tags": tags,
            "mappings": mappings,
            "cluster": self._get_cluster_info(),
            "keys": key_dict,
        }

    def _write_key_data_json(self, output_path: Path) -> dict:
        """
        Entry point for gathering all statistics keys from the cluster and saving them as a JS object.
        Output file: `web_app/js/keys.js`
        """
        logging.info("Collecting statistics keys from the cluster...")

        # Pull stat keys from the cluster
        collector = key_collector.KeyCollector(self.cluster_ip, self.username, self.password)
        key_dict = collector.get_tagged_squashed_dict()

        # Apply transformations: tagging and searchable keywords
        key_dict = self._transform_key_dict(key_dict)

        # Build the full structured dataset
        data = self._build_dataset(key_dict)

        # Ensure the parent output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write a JS variable assignment that defines `keyDict = {...}`
        with output_path.open("w", encoding="utf-8") as f:
            f.write("var keyDict = ")
            json.dump(data, f, indent=2)

        return data

    def _render_app(self, key_data: dict, output_path: Path) -> None:
        """
        Generate the HTML file for the web app using a Jinja2 template.
        Injects the processed stat key metadata, tags, mappings, etc.
        Output file: `web_app/index.html`
        """
        logging.info(f"Rendering HTML to {output_path}")

        # Load the Jinja2 template
        loader = PackageLoader("stat_key_browser", "templates")
        env = Environment(loader=loader)
        template = env.get_template("app_template.html")

        # Render the HTML template with the relevant values
        rendered = template.render(
            categories=key_data["categories"],
            keys=key_data["keys"],
            cat_mappings=key_data["mappings"]["categories"],
            key_mappings=key_data["mappings"]["keys"],
            tags=key_data["tags"],
            cluster=key_data["cluster"],
        )

        # Ensure output directory exists and write the file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            f.write(rendered)

    def build_browser(self) -> None:
        """
        The master control method:
        - Pulls cluster keys
        - Writes the JS metadata file
        - Renders the HTML frontend using a Jinja template
        """
        try:
            jskeys_path = JS_DIR / JSKEYS_FNAME
            html_path = OUTPUT_DIR / HTML_FNAME

            logging.info("Building stats browser UI...")

            # Pull and write JS key metadata
            key_data = self._write_key_data_json(jskeys_path)

            # Generate the main HTML file for browsing the keys
            self._render_app(key_data, html_path)

            logging.info("Browser generation complete.")
        except Exception as e:
            logging.error(f"Failed to build browser: {e}")
            raise
