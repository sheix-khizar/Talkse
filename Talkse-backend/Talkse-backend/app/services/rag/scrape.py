import os
import sys
import time
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

def fetch_page(url: str) -> str | None:
    headers = {"User-Agent": "Mozilla/5.0 (Talkse clinic content bot)"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"[Scrape Warning] Failed to fetch {url}: {e}")
        return None

def save_page(url: str, html: str, category: str, output_dir: str):
    path_part = urlparse(url).path.strip("/").replace("/", "_") or "index"
    out_dir = os.path.join(output_dir, category)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{path_part}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[Scrape] Saved {url} -> {out_path}")

def crawl_urls(url_list: list[tuple[str, str]], output_dir: str, delay_seconds: float = 1.0):
    """url_list: [(url, category), ...] where category is 'services', 'faq', 'doctors', 'blogs'."""
    for url, category in url_list:
        html = fetch_page(url)
        if html:
            save_page(url, html, category, output_dir)
        time.sleep(delay_seconds)  # be polite, don't hammer the clinic's server

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("[Scrape] Usage: python -m app.services.rag.scrape <tenant_id> <base_url>")
        print("[Scrape] Example: python -m app.services.rag.scrape clinic_042 https://www.realclinicwebsite.com")
        sys.exit(1)

    tenant_id = sys.argv[1]
    base_url = sys.argv[2].rstrip("/")
    output_dir = f"data/{tenant_id}/raw_html"

    # IMPORTANT: this list is a placeholder. For each real clinic, open their
    # site's sitemap (usually at <base_url>/sitemap.xml) and list every page
    # that has services, pricing, FAQ, or provider/doctor info. Add one tuple
    # per page: (full_url, category) where category is "services", "faq",
    # "doctors", or "blogs".
    urls = [
        (f"{base_url}/services/", "services"),
        (f"{base_url}/faq/", "faq"),
        (f"{base_url}/providers/", "doctors"),
    ]
    crawl_urls(urls, output_dir)
