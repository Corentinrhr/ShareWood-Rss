#!/usr/bin/env python3
# By LimeCat

import email.utils
import logging
import os
import secrets
import time
from datetime import datetime, timezone
from functools import wraps

import humanize
import requests
import yaml
from flask import Flask, Response, abort, request
from lxml import etree as et
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────────
try:
    with open("config.yml", "r") as ymlfile:
        cfgTitle = yaml.safe_load(ymlfile) or {}
        titleDict = cfgTitle.get("title") or {}
except FileNotFoundError:
    print("WARNING: config.yml not found")
    titleDict = {}

# ── Auth ──────────────────────────────────────────────────────────────────────
# Les variables d'environnement sont prioritaires sur config.yml

AUTH_USER = os.environ.get("RSS_USERNAME")
AUTH_PASS = os.environ.get("RSS_PASSWORD")
AUTH_ENABLED = bool(AUTH_USER and AUTH_PASS)

if AUTH_ENABLED:
    log.info("HTTP Basic Auth is ENABLED")
else:
    log.info("HTTP Basic Auth is DISABLED (open access)")

# ── Flask app ─────────────────────────────────────────────────────────────────

app = Flask(__name__)

# ── Requests session ──────────────────────────────────────────────────────────

session = requests.Session()
session.headers.update({"User-Agent": "Sharewood-RSS/1.0"})

retry = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504],
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)

BASE_URL = "https://www.sharewood.tv"


# ── Auth decorator ────────────────────────────────────────────────────────────

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if AUTH_ENABLED:
            auth = request.authorization
            if not auth:
                return Response(
                    "Authentication required",
                    401,
                    {"WWW-Authenticate": 'Basic realm="ShareWood RSS"'},
                )
            # secrets.compare_digest évite les timing attacks
            user_ok = secrets.compare_digest(
                auth.username.encode("utf-8"), AUTH_USER.encode("utf-8")
            )
            pass_ok = secrets.compare_digest(
                auth.password.encode("utf-8"), AUTH_PASS.encode("utf-8")
            )
            if not (user_ok and pass_ok):
                log.warning("Failed auth attempt from %s", request.remote_addr)
                return Response(
                    "Invalid credentials",
                    401,
                    {"WWW-Authenticate": 'Basic realm="ShareWood RSS"'},
                )
        return f(*args, **kwargs)
    return decorated


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_sharewood_data(url, params):
    try:
        response = session.get(url, params=params, timeout=(5, 20))
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []
    except requests.exceptions.RequestException as e:
        log.error("Sharewood API error: %s", e)
        return []


def parse_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return email.utils.format_datetime(dt.replace(tzinfo=timezone.utc))
    except Exception:
        return email.utils.formatdate(usegmt=True)


# ── Error handlers ────────────────────────────────────────────────────────────

@app.errorhandler(400)
def bad_request(e):
    return str(e), 400


@app.errorhandler(404)
def not_found(e):
    return str(e), 404


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def how_to():
    return (
        "<strong>Examples:</strong><br>"
        "/rss/PASSKEY/last-torrents?category=1<br>"
        "/rss/PASSKEY/last-torrents?subcategory=6<br>"
        "/rss/PASSKEY/search?name=watchmen&subcategory=9"
    )


@app.route("/health")
def health():
    return "ok", 200


@app.route("/rss/<string:passkey>/<string:apiAction>", methods=["GET"])
@requires_auth
def return_rss_file(passkey, apiAction):
    if not passkey or not passkey.isalnum() or len(passkey) != 32:
        abort(404, "Invalid passkey")

    category    = request.args.get("category",    type=int)
    subcategory = request.args.get("subcategory", type=int)
    limit       = request.args.get("limit", 50,   type=int)
    name        = request.args.get("name",         type=str)

    if name and len(name) > 100:
        abort(400, "Search query too long")

    api_params = {}
    current_cat_id = "0"

    if category and 1 <= category <= 7:
        api_params["category"] = category
        current_cat_id = str(category)

    if subcategory and 8 < subcategory <= 36:
        api_params["subcategory"] = subcategory
        current_cat_id = str(subcategory)

    api_params["limit"] = min(limit, 100)

    if name:
        api_params["name"] = name

    base_api = f"{BASE_URL}/api/{passkey}"

    if apiAction == "last-torrents":
        url = f"{base_api}/last-torrents"
    elif apiAction == "search" and name:
        url = f"{base_api}/search"
    else:
        abort(404, "Unknown action")

    torrents = get_sharewood_data(url, api_params)
    log.info(
        "action=%s passkey=***%s cat=%s items=%d",
        apiAction, passkey[-4:], current_cat_id, len(torrents)
    )

    # ── RSS generation ────────────────────────────────────────────────────────

    rss     = et.Element("rss", version="2.0")
    channel = et.SubElement(rss, "channel")

    title_node = et.SubElement(channel, "title")
    if name:
        title_node.text = f"ShareWood Search: {name}"
    else:
        title_node.text = f"ShareWood RSS: {titleDict.get(current_cat_id, 'Unknown')}"

    et.SubElement(channel, "description").text = "Sharewood RSS feed"
    et.SubElement(channel, "link").text = BASE_URL

    now_rfc = email.utils.formatdate(usegmt=True)
    et.SubElement(channel, "pubDate").text = now_rfc
    et.SubElement(channel, "ttl").text = "60"

    if not torrents:
        item = et.SubElement(channel, "item")
        et.SubElement(item, "title").text = "Sharewood unavailable"
        et.SubElement(item, "description").text = "Temporary API issue"
        et.SubElement(item, "pubDate").text = now_rfc
        et.SubElement(item, "guid", isPermaLink="false").text = f"error-{int(time.time())}"
    else:
        for torrent in torrents:
            item = et.SubElement(channel, "item")

            t_id      = torrent.get("id")
            t_name    = torrent.get("name", "Unnamed")
            t_slug    = torrent.get("slug", "torrent")
            t_size    = torrent.get("size", 0)
            t_created = torrent.get("created_at", "")

            et.SubElement(item, "title").text = str(t_name)

            human_size = (
                t_size if isinstance(t_size, str)
                else humanize.naturalsize(t_size, binary=True)
            )

            page_link = f"{BASE_URL}/torrents/{t_slug}.{t_id}"
            et.SubElement(item, "link").text = page_link
            et.SubElement(item, "guid", isPermaLink="false").text = f"{t_id}-{t_created}"
            et.SubElement(item, "pubDate").text = parse_date(t_created)

            desc_html = (
                f"<strong><a href='{page_link}'>{t_name}</a></strong><br/>"
                f"Size: {human_size}<br/>"
                f"Seeders: {torrent.get('seeders', 0)} | "
                f"Leechers: {torrent.get('leechers', 0)}<br/>"
                f"Added: {t_created}"
            )
            et.SubElement(item, "description").text = et.CDATA(desc_html)

            dl_url = f"{BASE_URL}/api/{passkey}/{t_id}/download"
            et.SubElement(
                item,
                "enclosure",
                url=dl_url,
                type="application/x-bittorrent",
            )

    xml_str = et.tostring(
        rss,
        pretty_print=True,
        encoding="utf-8",
        xml_declaration=True,
    )

    headers = {
        "Content-Type":  "application/rss+xml; charset=utf-8",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma":        "no-cache",
        "Expires":       "0",
        "Last-Modified": now_rfc,
    }

    return Response(xml_str, headers=headers)
