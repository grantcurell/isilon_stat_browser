import argparse
import logging
import os
import subprocess
from urllib.parse import urljoin, urlencode

import requests
import urllib3
from flask import Flask, request, Response, send_from_directory

from stat_key_browser.browser_builder import BrowserBuilder

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)

# Argument parsing
parser = argparse.ArgumentParser(description="Launch the OneFS stat browser proxy")
parser.add_argument("--host", default=os.getenv("ISILON_HOST"), help="Isilon cluster IP or hostname")
parser.add_argument("--user", default=os.getenv("ISILON_USER"), help="Isilon username")
parser.add_argument("--pass", dest="password", default=os.getenv("ISILON_PASS"), help="Isilon password")
args = parser.parse_args()

if not all([args.host, args.user, args.password]):
    raise SystemExit("❌ Must provide --host, --user, and --pass (or set ISILON_* environment variables)")

ISILON_HOST = args.host
ISILON_USER = args.user
ISILON_PASS = args.password
WEB_DIR = "web_app"

# Ensure key_cats.json and key_tags.json exist, or run hexaparse
DATA_DIR = os.path.join("stat_key_browser", "data")
cats_path = os.path.join(DATA_DIR, "key_cats.json")
tags_path = os.path.join(DATA_DIR, "key_tags.json")

if not (os.path.exists(cats_path) and os.path.exists(tags_path)):
    logging.info("🔍 Missing key_cats.json or key_tags.json — running hexaparse...")
    try:
        subprocess.run(["python", "hexaparse.py"], check=True)
        logging.info("✅ hexaparse completed.")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Failed to run hexaparse.py: {e}")
        raise SystemExit(1)

# Flask static setup
app = Flask(__name__, static_folder=WEB_DIR, static_url_path=None)

# ✅ Run build_browser at startup to generate static HTML and JS
with app.app_context():
    logging.info("⏳ Generating browser files...")
    builder = BrowserBuilder(ISILON_HOST, ISILON_USER, ISILON_PASS, store_ip=True)
    builder.build_browser()
    logging.info("✅ Browser files built.")


# Serve prebuilt static UI
@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)


# PAPI proxy
@app.route("/papi")
def proxy_papi():
    path = request.args.get("path")
    query_params = {k: v for k, v in request.args.items() if k != "path"}

    if not path:
        return "Missing required `path` parameter", 400

    papi_url = urljoin(f"https://{ISILON_HOST}:8080", path)
    if query_params:
        papi_url += "?" + urlencode(query_params)

    auth_payload = {
        "username": ISILON_USER,
        "password": ISILON_PASS,
        "services": ["platform"]
    }

    try:
        auth_resp = requests.post(
            f"https://{ISILON_HOST}:8080/session/1/session",
            json=auth_payload,
            verify=False
        )
    except Exception as e:
        return f"Failed to connect to OneFS: {e}", 502

    if auth_resp.status_code != 201:
        return f"Auth failed: {auth_resp.text}", 401

    session_cookies = auth_resp.cookies
    csrf_token = session_cookies.get('isicsrf')

    headers = {
        "Referer": f"https://{ISILON_HOST}:8080",
        "X-CSRF-Token": csrf_token
    }

    papi_resp = requests.get(
        papi_url,
        cookies=session_cookies,
        headers=headers,
        verify=False
    )

    return Response(
        papi_resp.content,
        status=papi_resp.status_code,
        content_type=papi_resp.headers.get("Content-Type", "application/json")
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
