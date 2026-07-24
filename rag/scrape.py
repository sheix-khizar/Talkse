import os
import time
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

BASE_URL = "https://www.skinspirit.com"
OUTPUT_DIR = "data/raw_html"

def fetch_page(url: str) -> str | None:
    headers = {"User-Agent": "Mozilla/5.0 (research demo bot)"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"[Scrape Warning] Failed to fetch {url}: {e}")
        return None

def save_page(url: str, html: str, category: str):
    path_part = urlparse(url).path.strip("/").replace("/", "_") or "index"
    out_dir = os.path.join(OUTPUT_DIR, category)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{path_part}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[Scrape] Saved {url} -> {out_path}")

def crawl_urls(url_list: list[tuple[str, str]], delay_seconds: float = 1.0):
    """url_list: [(url, category), ...] where category is 'services', 'faq', 'doctors', 'blogs'."""
    for url, category in url_list:
        html = fetch_page(url)
        if html:
            save_page(url, html, category)
        time.sleep(delay_seconds)  # be polite, don't hammer their server

if __name__ == "__main__":
    urls = [
        (f"{BASE_URL}/treatments/botox/", "services"),
        (f"{BASE_URL}/treatments/dermal-fillers/", "services"),
        (f"{BASE_URL}/faq/", "faq"),
        (f"{BASE_URL}/providers/", "doctors"),
        # add more real URLs you find by browsing the site's sitemap
    ]
    crawl_urls(urls)
