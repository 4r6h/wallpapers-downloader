#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WallpapersCraft Downloader (Python version)
- Fetches categories, resolutions, max pages
- JSON cache (24h)
- Retries failed downloads persistently with --retry flag
"""

import os, sys, json, time, re, argparse
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
    USE_BS4 = True
except ImportError:
    USE_BS4 = False
    print("[WARN] BeautifulSoup not found, using regex fallback. Install: pip install beautifulsoup4 requests")

# ── Configuration ────────────────────────────────────────────────────────
BASE_URL = "https://wallpaperscraft.com"
CACHE_DIR = Path.home() / ".cache" / "wallpaperscraft_downloader"
CACHE_FILE = CACHE_DIR / "cache.json"
CACHE_TTL = 86400  # 24 hours
OUTPUT_DIR = Path(os.environ.get("WALLCRAFT_DIR", Path.cwd() / "crafts"))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

FALLBACK_RESOLUTIONS = [
    "2160x3840","1440x2560","1350x2400","1080x1920","938x1668",
    "800x1420","800x1280","800x1200","720x1280","540x960",
    "480x854","480x800","360x640","320x480","320x240",
    "240x400","240x320","3415x3415","2780x2780","1280x1280",
    "1600x1200","1400x1050","1280x1024","1280x960","1152x864",
    "1024x768","1024x600","960x544","800x600",
    "3840x2400","3840x2160","2560x1600","2560x1440","2560x1080",
    "2560x1024","2048x1152","1920x1200","1920x1080","1680x1050",
    "1600x900","1440x900","1366x768","1280x800","1280x720"
]
FALLBACK_MAX_PAGES = {
    "all":8817,"3d":91,"60_favorites":3,"abstract":719,
    "animals":1039,"anime":229,"art":245,"black":49,
    "cars":468,"city":434,"dark":364,"fantasy":27,
    "flowers":460,"food":285,"holidays":95,"love":70,
    "macro":611,"minimalism":88,"motorcycles":69,"music":41,
    "nature":1898,"other":819,"smilies":3,"space":128,
    "sport":59,"hi-tech":22,"textures":289,"vector":83,
    "words":148
}

# ── Permanent failure exception ──────────────────────────────────────────
class PermanentFailure(Exception):
    """Raised when a URL returns a client error (4xx) that won't resolve."""
    pass

# ── Cache helpers ────────────────────────────────────────────────────────
def load_cache():
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text())
            age = time.time() - data.get("timestamp", 0)
            if age < CACHE_TTL:
                return data
        except Exception:
            pass
    return None

def save_cache(categories, resolutions, max_pages_dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp": time.time(),
        "categories": categories,
        "resolutions": resolutions,
        "max_pages": max_pages_dict
    }
    CACHE_FILE.write_text(json.dumps(data, indent=2))

# ── Web fetchers ─────────────────────────────────────────────────────────
def fetch_categories(session):
    url = f"{BASE_URL}/all/1920x1080/page1"
    try:
        r = session.get(url, timeout=30); r.raise_for_status()
        if USE_BS4:
            soup = BeautifulSoup(r.text, 'html.parser')
            cats = set()
            for a in soup.select('a[href^="/catalog/"]'):
                href = a.get('href')
                if href and '/all/' not in href:
                    slug = href.split('/catalog/')[-1].rstrip('/')
                    if slug: cats.add(slug)
            categories = ["all"] + sorted(cats)
        else:
            slugs = set(re.findall(r'href="/catalog/([a-z0-9_]+)(?:/[^"]*)*"', r.text))
            categories = ["all"] + sorted(slugs)
        return categories
    except Exception as e:
        print(f"[ERROR] Categories fetch failed: {e}")
        return list(FALLBACK_MAX_PAGES.keys())

def fetch_resolutions(session):
    url = f"{BASE_URL}/all/1920x1080/page1"
    try:
        r = session.get(url, timeout=30); r.raise_for_status()
        if USE_BS4:
            soup = BeautifulSoup(r.text, 'html.parser')
            res_set = set()
            for opt in soup.select('select[name="resolution"] option'):
                val = opt.get('value')
                if val and 'x' in val: res_set.add(val)
            resolutions = sorted(res_set, key=lambda x: (int(x.split('x')[0]), int(x.split('x')[1])))
        else:
            resolutions = sorted(set(re.findall(r'<option value="(\d+x\d+)"', r.text)),
                                key=lambda x: (int(x.split('x')[0]), int(x.split('x')[1])))
        return resolutions
    except Exception as e:
        print(f"[ERROR] Resolutions fetch failed: {e}")
        return FALLBACK_RESOLUTIONS

def get_max_pages(session, category, resolution):
    if category == "all":
        url = f"{BASE_URL}/all/{resolution}/page1"
    else:
        url = f"{BASE_URL}/catalog/{category}/{resolution}/page1"
    try:
        r = session.get(url, timeout=30); r.raise_for_status()
        pages = re.findall(r'/page(\d+)', r.text)
        return max(int(p) for p in pages) if pages else 1
    except Exception as e:
        print(f"[WARN] Max pages estimation failed: {e}")
        return FALLBACK_MAX_PAGES.get(category, 1)

# ── Download helpers with retry logic ────────────────────────────────────
def download_file(session, url, dest_path, retries=5, backoff=2):
    """
    Download a file with retries.
    Returns True on success, False on temporary failure after all retries.
    Raises PermanentFailure for 4xx errors immediately.
    """
    last_err = None
    for attempt in range(1, retries+1):
        try:
            r = session.get(url, stream=True, timeout=60)
            if r.status_code == 200:
                with open(dest_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            elif r.status_code in (404, 403, 410, 401):
                raise PermanentFailure(f"HTTP {r.status_code}")
            else:
                last_err = f"HTTP {r.status_code}"
        except PermanentFailure:
            raise  # re-raise to be caught by caller, no retry
        except Exception as e:
            last_err = str(e)
        if attempt < retries:
            time.sleep(backoff * attempt)
    print(f"  [TEMP FAIL] {url}: {last_err}")
    return False

def scrape_image_links(url, resolution, session):
    try:
        r = session.get(url, timeout=30); r.raise_for_status()
        links = re.findall(r'https://images\.wallpaperscraft\.com/image/single/[^"]+', r.text)
        links = [re.sub(r'300x168', resolution, l) for l in links]
        return sorted(set(links))
    except Exception as e:
        print(f"[ERROR] Scraping {url}: {e}")
        return []

# ── Persistent retry loop ────────────────────────────────────────────────
def retry_failed_forever(session, failed_list):
    if not failed_list:
        return
    print(f"\n[RETRY] {len(failed_list)} file(s) failed. Will keep retrying (Ctrl+C to stop).")
    while failed_list:
        print(f"  Remaining: {len(failed_list)}. Waiting 30 seconds...")
        time.sleep(30)
        new_failed = []
        for url, dest in failed_list:
            try:
                if download_file(session, url, dest, retries=5, backoff=3):
                    print(f"  [OK] {dest.name}")
                else:
                    new_failed.append((url, dest))
            except PermanentFailure:
                print(f"  [SKIP] {dest.name} (permanent error)")
        failed_list[:] = new_failed

# ── Download a page ──────────────────────────────────────────────────────
def download_page(session, category, resolution, page_num, failed_list):
    folder = OUTPUT_DIR / category
    folder.mkdir(parents=True, exist_ok=True)
    if category == "all":
        url = f"{BASE_URL}/all/{resolution}/page{page_num}"
    else:
        url = f"{BASE_URL}/catalog/{category}/{resolution}/page{page_num}"
    print(f"[INFO] Page {page_num}: {url}")
    links = scrape_image_links(url, resolution, session)
    if not links:
        print("[WARN] No images found on this page.")
        return 0
    count = 0
    for link in links:
        fname = Path(link).name
        dest = folder / fname
        if dest.exists():
            count += 1
            continue
        print(f"  [DOWNLOAD] {fname}")
        try:
            if download_file(session, link, dest):
                count += 1
            else:
                failed_list.append((link, dest))
        except PermanentFailure:
            print(f"  [SKIP] {fname} (permanent error)")
    print(f"[OK] Downloaded {count} image(s) from page {page_num}.")
    return count

# ── Interactive prompts ──────────────────────────────────────────────────
def prompt_choice(items, msg, multi=False):
    for i, item in enumerate(items, 1):
        print(f"  {i:3d}. {item}")
    while True:
        choice = input(msg).strip()
        if multi and choice.lower() in ('all', 'a'):
            return items
        try:
            if '-' in choice and multi:  # range
                start, end = choice.split('-')
                return items[int(start)-1 : int(end)]
            else:
                return [items[int(choice)-1]]
        except (ValueError, IndexError):
            print("[ERROR] Invalid selection. Try again.")

def interactive_mode(session, cache_data, args):
    # Resolution selection
    all_resolutions = cache_data["resolutions"]
    resolutions = prompt_choice(all_resolutions, "\nSelect resolution(s) (number, range, or 'all'): ", multi=True)
    # Category selection
    all_categories = cache_data["categories"]
    categories = prompt_choice(all_categories, "\nSelect category(s) (number, range, or 'all'): ", multi=True)
    # Page mode
    print("\nPage options:")
    print("  1. Specific page")
    print("  2. Page range")
    print("  3. All pages")
    mode = input("Choice [1/2/3]: ").strip()
    if mode == '1':
        page_num = int(input("Page number: "))
        page_mode = 'single'
    elif mode == '2':
        start = int(input("Start page: "))
        end = int(input("End page: "))
        page_mode = 'range'
    elif mode == '3':
        page_mode = 'all'
    else:
        print("[ERROR] Invalid mode, using 'all'.")
        page_mode = 'all'

    failed_list = []
    for res in resolutions:
        for cat in categories:
            max_pages = cache_data["max_pages"].get(f"{cat}|{res}")
            if not max_pages:
                print(f"[INFO] Fetching max pages for {cat} @ {res}...")
                max_pages = get_max_pages(session, cat, res)
                cache_data["max_pages"][f"{cat}|{res}"] = max_pages
                save_cache(cache_data["categories"], cache_data["resolutions"], cache_data["max_pages"])
            print(f"Category: {cat}, Resolution: {res}, Max pages: {max_pages}")

            if page_mode == 'single':
                download_page(session, cat, res, page_num, failed_list)
            elif page_mode == 'range':
                for p in range(start, end+1):
                    download_page(session, cat, res, p, failed_list)
            else:  # all
                for p in range(1, max_pages+1):
                    download_page(session, cat, res, p, failed_list)

    # After all pages, handle failures
    if failed_list:
        if args.retry:
            retry_failed_forever(session, failed_list)
        else:
            print(f"\n[INFO] {len(failed_list)} downloads failed temporarily. ")
            print("[INFO] Use --retry flag to keep retrying, or run the script again later.")
            # Save failed list to file
            fail_file = OUTPUT_DIR / "failed_downloads.txt"
            with open(fail_file, 'w') as f:
                for url, dest in failed_list:
                    f.write(f"{url} -> {dest}\n")
            print(f"[INFO] Failed URLs saved to {fail_file}")

def cli_mode(session, cache_data, args):
    # Resolution(s)
    if args.resolution:
        res_list = [r.strip() for r in args.resolution.split(',')]
    else:
        res_list = [cache_data["resolutions"][0]]
    # Category(s)
    if args.category:
        cat_list = [c.strip() for c in args.category.split(',')]
    else:
        cat_list = [cache_data["categories"][0]]
    # Page mode
    if args.page:
        try:
            page_specific = int(args.page)
            page_mode = 'single'
            start_page = page_specific
        except ValueError:
            if '-' in args.page:
                start_page, end_page = map(int, args.page.split('-'))
                page_mode = 'range'
            elif args.page.lower() == 'all':
                page_mode = 'all'
                start_page = 1
            else:
                print("[ERROR] Page must be number, range (1-5) or 'all'.")
                sys.exit(1)
    else:
        page_mode = 'all'
        start_page = 1

    failed_list = []
    for res in res_list:
        for cat in cat_list:
            max_pages = cache_data["max_pages"].get(f"{cat}|{res}")
            if not max_pages:
                print(f"[INFO] Fetching max pages for {cat} @ {res}...")
                max_pages = get_max_pages(session, cat, res)
                cache_data["max_pages"][f"{cat}|{res}"] = max_pages
                save_cache(cache_data["categories"], cache_data["resolutions"], cache_data["max_pages"])
            print(f"Category: {cat}, Resolution: {res}, Max pages: {max_pages}")

            if page_mode == 'single':
                download_page(session, cat, res, start_page, failed_list)
            elif page_mode == 'range':
                for p in range(start_page, end_page+1):
                    download_page(session, cat, res, p, failed_list)
            else:
                for p in range(1, max_pages+1):
                    download_page(session, cat, res, p, failed_list)

    if failed_list:
        if args.retry:
            retry_failed_forever(session, failed_list)
        else:
            print(f"\n[INFO] {len(failed_list)} downloads failed temporarily.")
            print("[INFO] Use --retry flag to keep retrying, or run the script again later.")
            fail_file = OUTPUT_DIR / "failed_downloads.txt"
            with open(fail_file, 'w') as f:
                for url, dest in failed_list:
                    f.write(f"{url} -> {dest}\n")
            print(f"[INFO] Failed URLs saved to {fail_file}")

# ── Main ─────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="WallpapersCraft Downloader (Python)")
    parser.add_argument('-r', '--resolution', help='Resolution(s) (comma-separated)')
    parser.add_argument('-c', '--category', help='Category(s) (comma-separated)')
    parser.add_argument('-p', '--page', help='Page number, range (1-10) or "all"')
    parser.add_argument('--no-cache', action='store_true', help='Force live fetch')
    parser.add_argument('--retry', action='store_true',
                        help='Keep retrying temporary failed downloads until success (or Ctrl+C)')
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({'User-Agent': UA})

    cache = load_cache()
    if args.no_cache or cache is None:
        print("[INFO] Fetching live data...")
        categories = fetch_categories(session)
        resolutions = fetch_resolutions(session)
        max_pages_dict = {}
        cache = {"categories": categories, "resolutions": resolutions, "max_pages": max_pages_dict}
        save_cache(categories, resolutions, max_pages_dict)
    else:
        print(f"[INFO] Using cache (age: {int((time.time() - cache['timestamp'])//60)} min).")

    if not cache["categories"] or not cache["resolutions"]:
        print("[ERROR] Could not load categories or resolutions."); sys.exit(1)

    if len(sys.argv) == 1:   # no CLI arguments -> interactive
        print("\n=== Interactive Mode ===")
        interactive_mode(session, cache, args)
    else:
        cli_mode(session, cache, args)

if __name__ == "__main__":
    main()