#!/usr/bin/env python3
"""Fetch all existing diary entries from the VTU API and save to previous_entries/."""
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

settings = json.loads((ROOT / "config" / "settings.json").read_text("utf-8"))
api = settings["api"]
base_url = api["base_url"].rstrip("/")
timeout = int(api.get("timeout_seconds", 30))

# --- login ---
session = requests.Session()
login_url = f"{base_url}{api['login_path']}"
print(f"Logging in to {login_url} ...")
resp = session.post(
    login_url,
    headers={"Content-Type": "application/json"},
    json={"email": os.getenv("VTU_EMAIL"), "password": os.getenv("VTU_PASSWORD")},
    timeout=timeout,
)
data = resp.json() if resp.content else {}
if not resp.ok or data.get("success") is not True:
    raise SystemExit(f"Login failed: {resp.status_code} | {data}")
print("Login OK")

# --- fetch all pages ---
list_path = api.get("diary_list_path", "/api/v1/student/internship-diaries")
page = 1
all_items = []
while True:
    url = f"{base_url}{list_path}?page={page}"
    print(f"Fetching {url} ...")
    r = session.get(url, headers=settings["auth"]["headers"], timeout=timeout)
    d = r.json() if r.content else {}
    if not r.ok or d.get("success") is not True:
        raise SystemExit(f"Fetch failed on page {page}: {r.status_code} | {d}")

    payload = d.get("data", {})
    next_page_url = None
    if isinstance(payload, dict):
        items = payload.get("data", [])
        next_page_url = payload.get("next_page_url")
    elif isinstance(payload, list):
        items = payload
    else:
        items = []

    all_items.extend(items)
    print(f"  page {page}: {len(items)} items (total so far: {len(all_items)})")

    if not next_page_url:
        break
    page += 1
    time.sleep(0.3)

print(f"\nTotal entries fetched: {len(all_items)}")

# --- save ---
out_dir = ROOT / "previous_entries"
out_dir.mkdir(exist_ok=True)

# Save everything in one file
all_path = out_dir / "all_entries.json"
all_path.write_text(json.dumps(all_items, indent=2, ensure_ascii=False), "utf-8")
print(f"Saved {all_path}")

# Also save the raw paginated responses for reference
raw_path = out_dir / "raw_api_response.json"
raw_path.write_text(json.dumps({"total": len(all_items), "entries": all_items}, indent=2, ensure_ascii=False), "utf-8")
print(f"Saved {raw_path}")

# Group by date and print summary
dates = sorted(set(item.get("date", "unknown") for item in all_items if isinstance(item, dict)))
print(f"\nDate range: {dates[0] if dates else '?'} to {dates[-1] if dates else '?'}")
print(f"Unique dates: {len(dates)}")
