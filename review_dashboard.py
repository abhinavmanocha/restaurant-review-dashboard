#!/usr/bin/env python3
"""
Restaurant Review Dashboard - Main Scraper
Fetches reviews for all configured restaurants and generates an HTML dashboard.
"""
import os, json, re, sys
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "restaurants.json")
OUTPUT_HTML = os.path.join(OUTPUT_DIR, "index.html")
OUTPUT_JSON = os.path.join(OUTPUT_DIR, "reviews_data.json")


def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"Config not found: {CONFIG_FILE}")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f).get("restaurants", [])


def scrape_renderseo(page, email, password):
    print("  Logging into RenderSEO...")
    page.goto("https://platform.renderseo.com/login", timeout=30000)
    page.wait_for_timeout(3000)
    page.fill('input[type="text"]', email)
    page.fill('input[type="password"]', password)
    page.click("button:has-text('LOG IN')")
    page.wait_for_timeout(8000)
    page.goto("https://platform.renderseo.com/review-mgmt#reviews", timeout=30000)
    page.wait_for_timeout(5000)
    for item in page.query_selector_all('.p-panelmenu-header-link, .p-menuitem-link'):
        if item.inner_text().strip() == 'REVIEWS':
            item.click()
            page.wait_for_timeout(4000)
            break
    page.wait_for_timeout(3000)
    return parse_renderseo(page.inner_text('body'))


def parse_renderseo(text):
    reviews = []
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        m = re.match(r'^On\s+(\d{4}/\d{1,2}/\d{1,2})$', s)
        if m:
            date_str = m.group(1)
            i += 1
            parts = []
            reply = []
            rating = None
            mode = 'text'
            while i < len(lines):
                line = lines[i]
                st = line.strip()
                if re.match(r'^\s*([1-5])\s*$', line):
                    rating = int(st)
                    i += 1
                    mode = 'reply'
                    continue
                if rating and st == '' and mode == 'reply':
                    i += 1
                    continue
                if re.match(r'^On\s+\d{4}/\d{1,2}/\d{1,2}$', st):
                    break
                skip = ['ADD/EDIT', 'EXPORT', 'SELECT', 'Store Code', 'LOCATION',
                        'REVIEW', 'RATING', 'RESPONSE', '5255', 'Santa Maria',
                        'Milton, ON', 'L9T6J5', 'Welcome', 'HOME', 'METRICS',
                        'KEYWORDS', 'OTHER REVIEWS', 'REPORTS', 'Reviews from',
                        'Your Reviews.', 'Review Management', 'St. Louis Bar']
                if not any(x in st for x in skip) and st:
                    if mode == 'text':
                        parts.append(st)
                    else:
                        reply.append(st)
                i += 1
            if rating:
                reviews.append({
                    'date_str': date_str,
                    'rating': rating,
                    'text': ' '.join(parts).strip() if parts else '',
                    'reply': ' '.join(reply).strip() if reply else '',
                    'sort_date': date_str.replace('/', '-')
                })
            continue
        i += 1
    return reviews


def scrape_gmaps(ctx, config):
    print("  Loading Google Maps...")
    page = ctx.new_page()
    try:
        page.goto(config["maps_url"], wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
    except:
        pass
    body = page.inner_text("body")
    rating = None
    total = None
    m = re.search(r'([\d.]+)\s*\(([\d,]+)\s+reviews?\)', body)
    if m:
        rating = float(m.group(1))
        total = m.group(2)
    else:
        m = re.search(r'barBURRITO\s*([\d.]+)', body)
        if m:
            rating = float(m.group(1))
        m = re.search(r'([\d,]+)\s*reviews?', body)
        if m:
            total = m.group(1)
    page.close()
    return {"rating": rating, "total_reviews": total}


def build_html(restaurants, all_reviews, gmaps_data):
    def sort_key(r):
        d = r.get("sort_date", r.get("date_str", ""))
        p = d.replace("-", "/").split("/")
        return (int(p[0]), int(p[1]), int(p[2])) if len(p) == 3 else (0, 0, 0)
    top5 = sorted(all_reviews, key=sort_key, reverse=True)[:5]
    cards = ""
    for rest in restaurants:
        c = rest.get("color", "#666")
        if rest["source"] == "renderseo":
            rr = [r for r in all_reviews if r.get("_rid") == rest["id"]]
            avg = round(sum(int(r["rating"]) for r in rr if r.get("rating")) / len(rr), 1) if rr else "N/A"
            rows = f'<div class=stat-row><span class=stat-label>Avg Rating</span><span class=stat-value>{avg}</span></div><div class=stat-row><span class=stat-label>Reviews (30d)</span><span class=stat-value>{len(rr)}</span></div>'
        else:
            d = gmaps_data.get(rest["id"], {})
            rows = ""
            if d.get("rating"):
                rows += f'<div class=stat-row><span class=stat-label>Google Rating</span><span class=stat-value>{d["rating"]}</span></div>'
            if d.get("total_reviews"):
                rows += f'<div class=stat-row><span class=stat-label>Total Reviews</span><span class=stat-value>{d["total_reviews"]}</span></div>'
        cards += f'<div class=stat-card style="border-top:4px solid {c}"><h3>{rest["name"]}</h3><p class=stat-address>{rest.get("address","")}</p>{rows}</div>'
    rlist = ""
    for r in top5:
        ri = next((x for x in restaurants if x["id"] == r.get("_rid")), restaurants[0] if restaurants else {})
        c = ri.get("color", "#666")
        sn = ri.get("short", ri.get("name", "?"))
        stars = chr(9733) * int(r.get("rating", 0)) + chr(9734) * (5 - int(r.get("rating", 0))) if r.get("rating") else ""
        rlist += f'<div class=review-card style="border-left:4px solid {c}"><div class=review-header><span class=restaurant-badge style="background:{c}">{sn}</span><span class=review-date>{r.get("date_str","")}</span><span class=review-stars style="color:{c}">{stars}</span></div><div class=review-body><p>{r.get("text","")}</p></div>'
        if r.get("reply"):
            rlist += f'<div class=review-reply><strong>Reply:</strong> {r["reply"]}</div>'
        rlist += "</div>"
    now = datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Restaurant Review Dashboard</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:"Inter",sans-serif;background:#f5f5f7;color:#1d1d1f;padding:32px;max-width:1200px;margin:0 auto}}
.dashboard-header{{margin-bottom:32px}}
.dashboard-header h1{{font-size:28px;font-weight:800;letter-spacing:-0.5px}}
.dashboard-header p{{color:#6e6e73;font-size:14px}}
.last-updated{{color:#6e6e73;font-size:12px;margin-top:4px}}
.stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin-bottom:32px}}
.stat-card{{background:white;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.08)}}
.stat-card h3{{font-size:15px;font-weight:700;margin-bottom:2px}}
.stat-address{{font-size:12px;color:#6e6e73;margin-bottom:12px}}
.stat-row{{display:flex;justify-content:space-between;padding:4px 0;font-size:14px}}
.stat-label{{color:#6e6e73}}
.stat-value{{font-weight:600}}
.section-title{{font-size:20px;font-weight:700;margin:24px 0 16px;letter-spacing:-0.3px}}
.reviews-list{{display:flex;flex-direction:column;gap:12px}}
.review-card{{background:white;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.08)}}
.review-header{{display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap}}
.restaurant-badge{{padding:2px 10px;border-radius:4px;color:white;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px}}
.review-date{{font-size:12px;color:#6e6e73}}
.review-stars{{font-size:14px;letter-spacing:1px}}
.review-body p{{font-size:14px;line-height:1.6;color:#1d1d1f}}
.review-reply{{margin-top:10px;padding:10px 14px;background:#f5f5f7;border-radius:8px;font-size:13px;color:#515154}}
@media(max-width:768px){{body{{padding:16px}}}}
</style></head><body>
<div class=dashboard-header><h1>Restaurant Review Dashboard</h1><p>All reviews across your locations</p><p class=last-updated>Last updated: {now}</p></div>
<div class=stats-grid>{cards}</div>
<h2 class=section-title>Top 5 Most Recent Reviews</h2>
<div class=reviews-list>{rlist or '<p style="color:#6e6e73">No reviews found yet.</p>'}</div>
</body></html>"""


def main():
    print("=" * 60)
    print("  RESTAURANT REVIEW DASHBOARD")
    print("=" * 60)
    config = load_config()
    print(f"  Loaded {len(config)} restaurant(s)\n")
    all_reviews = []
    gmaps_data = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        for rest in config:
            print(f"[{rest['id']}] {rest['name']}...")
            if rest["source"] == "renderseo":
                page = ctx.new_page()
                try:
                    for r in scrape_renderseo(page, rest["renderseo_email"], rest["renderseo_password"]):
                        r["_rid"] = rest["id"]
                        all_reviews.append(r)
                    print(f"  Found {sum(1 for r in all_reviews if r.get('_rid')==rest['id'])} reviews")
                except Exception as e:
                    print(f"  Error: {e}")
                page.close()
            elif rest["source"] == "google_maps":
                try:
                    gmaps_data[rest["id"]] = scrape_gmaps(ctx, rest)
                except Exception as e:
                    print(f"  Error: {e}")
        browser.close()
    html = build_html(config, all_reviews, gmaps_data)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_HTML, "w") as f:
        f.write(html)
    with open(OUTPUT_JSON, "w") as f:
        json.dump({"last_updated": datetime.now(timezone.utc).isoformat(), "count": len(all_reviews)}, f, indent=2)
    print(f"\nDashboard: {OUTPUT_HTML}")
    print("Done!")


if __name__ == "__main__":
    main()
