#!/usr/bin/env python3
"""
Main CLI to fetch leads from Meta Graph API, normalize, dedupe and persist seen IDs.

Usage examples:
  python src/fetcher.py --since 2025-07-01T00:00:00+0000 --output json
  python src/fetcher.py --output csv
  python src/fetcher.py --dry-run
  python src/fetcher.py --mock-sample   # use data/meta_leads_sample.json, no API call
"""

from __future__ import annotations
import os
import sys
import json
import argparse
import logging
import time
from typing import Optional, List, Dict, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

from src.utils.db import LeadDB

# Load env
load_dotenv()

# Config from env (with sensible defaults)
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
LEAD_FORM_ID = os.getenv("LEAD_FORM_ID")
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v16.0")
GRAPH_API_BASE = os.getenv("GRAPH_API_BASE", "https://graph.facebook.com")
DB_PATH = os.getenv("DB_PATH", "data/seen_leads.db")
PAGE_SIZE = int(os.getenv("PAGE_SIZE", "100"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("furnishka-leads")

def make_session(total_retries: int = 3, backoff: float = 0.5) -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=total_retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

SESSION = make_session()

def build_url(form_id: str) -> str:
    # form_id usually like "1234567890"
    # use full path: https://graph.facebook.com/v24.0/{form_id}/leads
    return f"{GRAPH_API_BASE}/{GRAPH_API_VERSION}/{form_id}/leads"

def fetch_leads(access_token: str, form_id: str, since: Optional[str] = None, page_size: int = PAGE_SIZE) -> List[Dict[str, Any]]:
    """
    Fetch all pages of leads from the Graph API. Returns list of raw lead dicts.
    """
    if not access_token:
        raise RuntimeError("META_ACCESS_TOKEN is not set. Copy .env.sample to .env and add your token.")

    url = build_url(form_id)
    params = {"access_token": access_token, "fields": "field_data,created_time,id", "limit": page_size}
    if since:
        params["since"] = since

    leads: List[Dict[str, Any]] = []
    while url:
        logger.info(f"Fetching: {url}")
        resp = SESSION.get(url, params=params, timeout=30)
        # If server error, SESSION retry should handle; we still guard
        if resp.status_code >= 500:
            logger.warning("Server error %s. Sleeping 1s and retrying.", resp.status_code)
            time.sleep(1)
            resp = SESSION.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        page_items = data.get("data") if isinstance(data, dict) else data
        if page_items:
            leads.extend(page_items)
            logger.info("Fetched %d items", len(page_items))
        else:
            logger.info("No data in page response")

        # handle pagination
        paging = data.get("paging", {}) if isinstance(data, dict) else {}
        url = paging.get("next")
        # After the first request, pass params=None so paging.next works directly
        params = None

    logger.info("Total raw leads fetched: %d", len(leads))
    return leads

def normalize_lead(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a Graph lead object to a simple dict.
    Extract from field_data (list of {name, values})
    """
    lead_id = raw.get("id")
    created_time = raw.get("created_time")
    name = None
    email = None
    phone = None

    for field in raw.get("field_data", []) or []:
        key = (field.get("name") or "").lower()
        vals = field.get("values") or []
        if isinstance(vals, str):
            vals = [vals]
        val = vals[0] if vals else None
        if not val:
            continue
        if "email" in key:
            email = email or val.strip().lower()
        elif "name" in key or "full_name" in key or "first_name" in key:
            name = name or val.strip()
        elif "phone" in key or "mobile" in key:
            phone = phone or val.strip()
        else:
            # unknown field, ignore or you may add to raw
            pass

    # fallback direct fields
    email = email or raw.get("email") or raw.get("email_address")
    phone = phone or raw.get("phone") or raw.get("phone_number")
    name = name or raw.get("name") or raw.get("full_name")

    return {
        "lead_id": str(lead_id) if lead_id is not None else None,
        "created_time": created_time,
        "name": name,
        "email": email,
        "phone": phone,
        "raw": raw
    }

def write_output(new_leads: List[Dict[str, Any]], output: str = "json") -> None:
    if not new_leads:
        logger.info("No new leads to write.")
        return
    if output == "json":
        with open("new_leads.json", "w", encoding="utf-8") as f:
            json.dump(new_leads, f, indent=2, ensure_ascii=False)
        logger.info("Wrote %d leads to new_leads.json", len(new_leads))
    else:
        import csv
        keys = set()
        for l in new_leads:
            keys.update(l.keys())
        # ensure deterministic order: prefer main fields
        fieldnames = ["lead_id", "name", "email", "phone", "created_time"]
        extra = sorted(k for k in keys if k not in fieldnames)
        fieldnames.extend(extra)
        with open("new_leads.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in new_leads:
                # flatten raw to string for CSV if present
                r = row.copy()
                if "raw" in r:
                    r["raw"] = json.dumps(r["raw"], separators=(",", ":"), ensure_ascii=False)
                writer.writerow(r)
        logger.info("Wrote %d leads to new_leads.csv", len(new_leads))

def load_sample(path: str = "data/meta_leads_sample.json") -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        logger.error("Sample file not found: %s", path)
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_args():
    p = argparse.ArgumentParser(description="Fetch Meta leads from a Lead Ads form")
    p.add_argument("--since", help="ISO timestamp to fetch leads since", default=None)
    p.add_argument("--output", choices=["json", "csv"], default="json")
    p.add_argument("--db", help="Path to seen-leads DB", default=DB_PATH)
    p.add_argument("--dry-run", action="store_true", help="Don't write to DB, just show")
    p.add_argument("--max-pages", type=int, default=None, help="Limit pages fetched (useful for testing)")
    p.add_argument("--mock-sample", action="store_true", help="Load leads from data/meta_leads_sample.json (no API calls)")
    return p.parse_args()

def main():
    args = parse_args()
    # Validate if not mock
    if not args.mock_sample and (not ACCESS_TOKEN or not LEAD_FORM_ID):
        logger.error("ACCESS_TOKEN and LEAD_FORM_ID must be set in .env or use --mock-sample")
        sys.exit(1)

    db = LeadDB(args.db)
    try:
        if args.mock_sample:
            raw_leads = load_sample()
            logger.info("Loaded %d sample leads", len(raw_leads))
        else:
            raw_leads = fetch_leads(ACCESS_TOKEN, LEAD_FORM_ID, since=args.since)
        new_leads = []
        for raw in raw_leads:
            normalized = normalize_lead(raw)
            lid = normalized.get("lead_id")
            if not lid:
                logger.warning("Skipping lead with no id (raw=%s)", raw)
                continue
            if not normalized.get("email") and not normalized.get("phone"):
                logger.error("Skipping lead %s missing contact info", lid)
                continue
            if db.is_seen(lid):
                logger.debug("Already seen: %s", lid)
                continue
            # add to list
            new_leads.append({
                "lead_id": normalized.get("lead_id"),
                "name": normalized.get("name"),
                "email": normalized.get("email"),
                "phone": normalized.get("phone"),
                "created_time": normalized.get("created_time"),
                "raw": normalized.get("raw")
            })
            if not args.dry_run:
                db.mark_seen(lid)

        write_output(new_leads, output=args.output)
        logger.info("Fetched %d raw leads, %d new leads", len(raw_leads), len(new_leads))
    finally:
        db.close()

if __name__ == "__main__":
    main()
