"""
28Hse Hong Kong Rental Property Scraper
Crawls rental listings across Hong Kong Island, Kowloon and New Territories.
Outputs: data/raw/hk_rental_listings.csv
"""

import csv
import re
import time
import random
import os
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# ─── Configuration ───────────────────────────────────────────────────────────

# Region mapping from URL pattern
REGION_MAP = {
    "a1": "Hong Kong Island",
    "a2": "Kowloon",
    "a3": "New Territories",
}

BASE_URL = "https://www.28hse.com/rent/apartment/page-{page}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
}

# How many pages to scrape (set a limit for safety, ~15 items per page)
# 1286 total pages available, but we target ~3000-5000 listings
MAX_PAGES = 300  # ~4500 listings

DELAY_MIN = 1.0   # seconds between requests
DELAY_MAX = 2.5

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data", "raw")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "hk_rental_listings.csv")


# ─── Parsing Helpers ─────────────────────────────────────────────────────────

def extract_region(url_path: str) -> str:
    """Extract region (HK Island / Kowloon / NT) from listing URL."""
    m = re.search(r"/a(\d+)/", url_path)
    if m:
        return REGION_MAP.get(m.group(1), "Unknown")
    return "Unknown"


def extract_district(item) -> str:
    """Extract district name (e.g. 黃大仙, 青衣)."""
    district_el = item.select_one(".district_area a")
    if district_el:
        return district_el.get_text(strip=True)
    return ""


def extract_estate(item) -> str:
    """Extract estate name (e.g. 薈鳴, 偉景花園)."""
    links = item.select(".district_area a")
    if len(links) >= 2:
        return links[1].get_text(strip=True)
    return ""


def extract_floor_level(item) -> str:
    """Extract floor level (低層/中層/高層)."""
    desc = item.select_one(".unit_desc")
    if desc:
        text = desc.get_text(strip=True)
        # Check for low/mid/high
        for level in ["高層", "中層", "低層"]:
            if level in text:
                return level
        return text[:20] if text else ""
    return ""


def extract_size(item) -> float:
    """Extract usable area in sq ft."""
    price_area = item.select_one(".areaUnitPrice")
    if price_area:
        text = price_area.get_text(strip=True)
        m = re.search(r"(\d[\d,]*)", text.replace("實用面積:", "").replace("呎", ""))
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                pass
    return 0.0


def extract_price(item) -> float:
    """Extract monthly rent in HKD."""
    price_el = item.select_one(".ui.right.floated.green.large.label")
    if price_el:
        text = price_el.get_text(strip=True)
        m = re.search(r"\$?([\d,]+)", text)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                pass
    return 0.0


def extract_layout(item) -> str:
    """Extract layout/room type (e.g. 2房, 開放式)."""
    # First tag in tagLabels usually has layout info
    tags = item.select(".tagLabels .ui.label")
    if tags:
        first = tags[0].get_text(strip=True)
        # It might be like "2 房 , 1 浴室" or "開放式間隔"
        return first
    return ""


def extract_tags(item) -> str:
    """Extract all tags as a semicolon-separated string."""
    tags = item.select(".tagLabels .ui.label")
    return "; ".join(t.get_text(strip=True) for t in tags)


def extract_listing_id(item) -> str:
    """Extract unique property ID."""
    link = item.select_one("a.detail_page")
    if link:
        href = link.get("href", "")
        m = re.search(r"property-(\d+)", href)
        if m:
            return m.group(1)
    return ""


def extract_posted_time(item) -> str:
    """Extract when the listing was posted."""
    time_el = item.select_one(".ui.label .clock")
    if time_el:
        parent = time_el.parent
        if parent:
            return parent.get_text(strip=True)
    # Fallback
    time_el = item.select_one(".description .ui.label")
    if time_el:
        return time_el.get_text(strip=True)
    return ""


# ─── Scraper ─────────────────────────────────────────────────────────────────

def scrape_page(page_num: int) -> list[dict]:
    """Scrape a single page of rental listings."""
    url = BASE_URL.format(page=page_num)
    print(f"  Fetching page {page_num}...", end=" ")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"FAILED: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    items = soup.select(".property_item")
    print(f"found {len(items)} listings")

    listings = []
    for item in items:
        try:
            link = item.select_one("a.detail_page")
            href = link.get("href", "") if link else ""
            listing = {
                "listing_id": extract_listing_id(item),
                "region": extract_region(href),
                "district": extract_district(item),
                "estate": extract_estate(item),
                "floor_level": extract_floor_level(item),
                "size_sqft": extract_size(item),
                "price_hkd": extract_price(item),
                "layout": extract_layout(item),
                "tags": extract_tags(item),
                "posted_time": extract_posted_time(item),
                "url": href,
                "scraped_at": datetime.now().isoformat(),
            }
            # Only include listings with valid price
            if listing["price_hkd"] > 0:
                listings.append(listing)
        except Exception as e:
            print(f"  Error parsing item: {e}")
            continue

    return listings


def run_scraper(max_pages: int = MAX_PAGES):
    """Run the scraper across multiple pages."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_listings = []
    consecutive_empty = 0

    for page in range(1, max_pages + 1):
        listings = scrape_page(page)
        all_listings.extend(listings)
        print(f"  Running total: {len(all_listings)} listings")

        # If we get no results for 3 consecutive pages, assume we've reached the end
        if len(listings) == 0:
            consecutive_empty += 1
            if consecutive_empty >= 3:
                print("No more listings found. Stopping.")
                break
        else:
            consecutive_empty = 0

        # Polite delay between requests
        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        time.sleep(delay)

    # Write to CSV
    fieldnames = [
        "listing_id", "region", "district", "estate", "floor_level",
        "size_sqft", "price_hkd", "layout", "tags",
        "posted_time", "url", "scraped_at"
    ]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_listings)

    print(f"\nDone! {len(all_listings)} listings saved to {OUTPUT_FILE}")
    return all_listings


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    pages = MAX_PAGES
    if len(sys.argv) > 1:
        try:
            pages = int(sys.argv[1])
        except ValueError:
            print(f"Usage: python scraper.py [max_pages]")
            sys.exit(1)

    print(f"🚀 28Hse Rental Scraper")
    print(f"   Target: {pages} pages (~{pages * 15} listings)")
    print(f"   Output: {OUTPUT_FILE}")
    print()

    run_scraper(max_pages=pages)
