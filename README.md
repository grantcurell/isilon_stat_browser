[![Master Build Status](https://travis-ci.org/Isilon/isilon_stat_browser.svg?branch=master)](https://travis-ci.org/Isilon/isilon_stat_browser)
[![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/isilon/isilon_stat_browser.svg)](http://isitmaintained.com/project/isilon/isilon_stat_browser)
[![Percentage of issues still open](http://isitmaintained.com/badge/open/isilon/isilon_stat_browser.svg)](http://isitmaintained.com/project/isilon/isilon_stat_browser)

# Statistics Key Browser

This repository is part of the Isilon SDK and provides a tool for browsing the statistics keys exposed by OneFS. The statistics key browser is a Python-generated, single-page web application that displays all available statistics keys from a PowerScale cluster, categorized and tagged for easier exploration.

## Overview

The `build_stat_browser.py` script connects to your PowerScale cluster using the official `isilon_sdk` Python bindings, queries the Platform API (PAPI) for all available statistics keys, applies human-readable categories and tags, and then generates an HTML page with JavaScript data. The result is a static website you can open directly in your browser.

## Requirements

### Runtime

- Python 3.6 or later (tested with 3.11)
- A web browser that supports JavaScript:
  - Chrome
  - Firefox
  - Edge
  - Safari

### Python Packages

Install dependencies using:

```
pip install -r requirements.txt
```

For development:

```
pip install -r requirements-dev.txt
```

### SDK Bindings

This tool uses the official Python bindings for OneFS 9.4+:
https://pypi.org/project/isilon-sdk/

Make sure the version of the SDK installed matches your cluster version or defaults to the most recent supported version (currently `v9_10_0`).

## Usage

### Building the Stat Browser

To generate a complete, self-contained `web_app/index.html` from a cluster:

```
python build_stat_browser.py --cluster <IP> --user <username> --password <password>
```

The script will:
- Connect to your cluster and detect the OneFS version
- Use the matching version of the SDK bindings
- Query all statistics keys from the PAPI
- Apply tags and categories (from `*.hexa` definitions)
- Write `web_app/index.html` and `web_app/js/keys.js`

### Viewing the Browser

After building, open:

```
web_app/index.html
```

in any modern web browser to browse the stats.

### Building the JSON Data

You can regenerate the `.json` files from the `.hexa` inputs using:

```
python hexaparse.py
```

This will generate:

- `stat_key_browser/data/key_tags.json`
- `stat_key_browser/data/key_cats.json`

These are used to annotate and categorize the statistics keys queried from the cluster.

### Running Tests

Run all unit tests:

```
make unittests
```

Run with coverage:

```
make coverage
```

## Distribution

To package a ZIP archive for distribution (includes all files required to run the app offline):

```
make dist BUILD_BROWSER_ARGS='-c <cluster_ip> -u <username> -p <password>'
```

The result will be `isilon_stat_browser_<version>.zip`.

You can also generate the ZIP manually:

```
python build_stat_browser.py --cluster <ip> --user <user> --password <pw>
```

Then zip the contents of the `web_app/` and any other desired files.

## File Descriptions

- `build_stat_browser.py` – Main entry point; queries the cluster, builds `index.html`
- `hexaparse.py` – Converts `.hexa` format to `.json`
- `stat_key_browser/browser_builder.py` – Coordinates JSON creation, templating
- `stat_key_browser/tagger.py` – Tags statistics keys
- `stat_key_browser/categorizer.py` – Categorizes statistics keys
- `stat_key_browser/key_collector.py` – Connects to cluster and fetches all stat keys
- `stat_key_browser/cluster_config.py` – Cluster connection and version logic
- `stat_key_browser/data/key_tags.hexa` – Human-readable tagging definitions
- `stat_key_browser/data/key_cats.hexa` – Human-readable categorization definitions
- `stat_key_browser/data/key_tags.json` – Auto-generated from `key_tags.hexa`
- `stat_key_browser/data/key_cats.json` – Auto-generated from `key_cats.hexa`
- `web_app/index.html` – Final stat browser output
- `web_app/js/keys.js` – Final annotated statistics key dictionary in JS
- `stat_key_browser/templates/app_template.html` – Main HTML template

## Release Process

To cut a release:

1. Tag the commit:

   ```
   git tag -a v0.0.1 -m "version 0.0.1"
   git push origin v0.0.1
   ```

2. Build the zip:

   ```
   make dist BUILD_BROWSER_ARGS='-c <cluster IP> -u <username> -p <password>'
   ```

3. Attach the generated `.zip` to a new GitHub release under the `Releases` tab.
