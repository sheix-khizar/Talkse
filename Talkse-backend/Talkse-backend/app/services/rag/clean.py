from bs4 import BeautifulSoup

NOISE_TAGS = ["nav", "header", "footer", "script", "style", "form", "aside"]
NOISE_CLASSES = ["cookie-banner", "site-header", "site-footer", "menu", "advertisement"]

def extract_clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in NOISE_TAGS:
        for el in soup.find_all(tag):
            el.decompose()

    for cls in NOISE_CLASSES:
        for el in soup.find_all(class_=cls):
            el.decompose()

    main = soup.find("main") or soup.find(id="content") or soup.body or soup
    text = main.get_text(separator="\n", strip=True)

    # collapse excess blank lines
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines)

if __name__ == "__main__":
    import os
    RAW_DIR = "data/raw_html"
    CLEAN_DIR = "data/clean_text"
    
    if not os.path.exists(RAW_DIR):
        print(f"Directory {RAW_DIR} not found. Please run scrape.py first.")
        import sys
        sys.exit(1)
        
    for category in os.listdir(RAW_DIR):
        cat_path = os.path.join(RAW_DIR, category)
        if not os.path.isdir(cat_path):
            continue
            
        out_cat_path = os.path.join(CLEAN_DIR, category)
        os.makedirs(out_cat_path, exist_ok=True)
        
        for fname in os.listdir(cat_path):
            if not fname.endswith(".html"):
                continue
                
            in_path = os.path.join(cat_path, fname)
            out_path = os.path.join(out_cat_path, fname.replace(".html", ".txt"))
            
            with open(in_path, "r", encoding="utf-8") as f:
                html = f.read()
                
            clean_text = extract_clean_text(html)
            
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(clean_text)
                
            print(f"[Clean] {in_path} -> {out_path}")
