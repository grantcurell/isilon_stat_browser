"""Manage the creation of the key browser."""

import json
import logging
from pathlib import Path

from jinja2 import Environment, PackageLoader

import stat_key_browser.cluster_config as cluster_config
import stat_key_browser.search_terms as search_terms
from stat_key_browser.tagger import Tagger
from stat_key_browser.categorizer import Categorizer
import stat_key_browser.key_collector as key_collector
import stat_key_browser.mapper as mapper
from stat_key_browser.cluster_config import ApiException

OUTPUT_DIR = Path("web_app")
JS_DIR = OUTPUT_DIR / "js"
HTML_FNAME = "index.html"
JSKEYS_FNAME = "keys.js"

UNKNOWN_RELEASE = "unknown"


class BrowserBuilder:
    """
    Generate an HTML file representing the stat key browser app.

    Inputs: List of keys from cluster via PAPI, tagging and categorization.
    Outputs: index.html and keys.js
    """

    def __init__(self, cluster_ip: str, username: str, password: str, store_ip: bool):
        self.cluster_ip = cluster_ip
        self.username = username
        self.password = password
        self.store_ip = store_ip

    def _get_cluster_info(self) -> dict:
        try:
            release = cluster_config.get_release(self.cluster_ip, self.username, self.password)
        except ApiException:
            logging.warning("Unable to determine OneFS version via SDK")
            release = UNKNOWN_RELEASE
        return {
            "release": release,
            "host": self.cluster_ip if self.store_ip else None,
        }

    def _transform_key_dict(self, key_dict: dict) -> dict:
        tagger = Tagger()
        key_dict = tagger.tag_keys(key_dict)
        search_terms.add_to_dict(key_dict)
        return key_dict

    def _build_dataset(self, key_dict: dict) -> dict:
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
        """Write keys to a JS file used by the browser."""
        logging.info("Collecting statistics keys from the cluster...")
        collector = key_collector.KeyCollector(self.cluster_ip, self.username, self.password)
        key_dict = collector.get_tagged_squashed_dict()
        key_dict = self._transform_key_dict(key_dict)
        data = self._build_dataset(key_dict)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            f.write("var keyDict = ")
            json.dump(data, f, indent=2)

        return data

    def _render_app(self, key_data: dict, output_path: Path) -> None:
        logging.info(f"Rendering HTML to {output_path}")
        loader = PackageLoader("stat_key_browser", "templates")
        env = Environment(loader=loader)
        template = env.get_template("app_template.html")

        rendered = template.render(
            categories=key_data["categories"],
            keys=key_data["keys"],
            cat_mappings=key_data["mappings"]["categories"],
            key_mappings=key_data["mappings"]["keys"],
            tags=key_data["tags"],
            cluster=key_data["cluster"],
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            f.write(rendered)

    def build_browser(self) -> None:
        """Generate the JS and HTML files for the stat key browser UI."""
        try:
            jskeys_path = JS_DIR / JSKEYS_FNAME
            html_path = OUTPUT_DIR / HTML_FNAME

            logging.info("Building stats browser UI...")
            key_data = self._write_key_data_json(jskeys_path)
            self._render_app(key_data, html_path)
            logging.info("Browser generation complete.")
        except Exception as e:
            logging.error(f"Failed to build browser: {e}")
            raise
