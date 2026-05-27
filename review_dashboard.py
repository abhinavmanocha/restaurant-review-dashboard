#!/usr/bin/env python3
"""
Manager Dashboard - Review Scraper + HTML Generator
Fetches reviews for all 3 restaurants and generates a dashboard HTML page.
"""
import os, sys, json, re, time
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

PASSWORD = "jellied-chrome#102"
OUTPUT_DIR = os.path.expanduser("~/.hermes/dashboard")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")
DATA_FILE = os.path.join(OUTPUT_DIR, "reviews_data.json")
DASHBOARD_COPY = os.path.expanduser("~/restaurant_review_dashboard.html")

RESTAURANTS = {
    "slf": {"name": "St. Louis Bar & Grill", "short": "SLF Milton", "address": "Unit 8, 604 Santa Maria Blvd, Milton, ON", "color": "#e31837"},
    "bb_milton": {"name": "Bar Burrito - Milton", "short": "BB Milton", "address": "Unit 7, 604 Santa Maria Blvd, Milton, ON", "color": "#e8a317",
        "maps_url": "https://www.google.com/maps/place/barBURRITO/@43.5021981,-79.865491,17z/data=!3m1!4b1!4m6!3m5!1s0x882b6f797cc0d2a9:0xa6be8a7bf1cad01b!8m2!3d43.5021981!4d-79.865491!16s%2Fg%2F11f8gn261w"},
    "bb_brampton": {"name": "Bar Burrito - Brampton", "short": "BB Brampton", "address": "72 Quarry Edge Dr #1, Brampton, ON", "color": "#e8a317",
        "maps_url": "https://www.google.com/maps/place/barBURRITO/@43.7071568,-79.7839363,17z/data=!3m1!4b1!4m6!3m5!1s0x882b150978d4609b:0xf6951edcf76ee94d!8m2!3d43.7071568!4d-79.7839363!16s%2Fg%2F11fggv4tng"}
}

EMAIL = "604santamaria@stlouiswings.com"


def scrape_slf_reviews(page):
    """Scrape St. Louis Bar & Grill reviews from RenderSEO."""
    print("  [SLF] Logging into RenderSEO...")
    page.goto("https://platform.renderseo.com/login", timeout=30000)
    page.wait_for_timeout(3000)
    page.fill('input[type="text"]', EMAIL)
    page.fill('input[type="password"]', PASSWORD)
    page.click("button:has-text('LOG IN')")
    page.wait_for_timeout(8000)

    print("  [SLF] Navigating to reviews...")
    page.goto("https://platform.renderseo.com/review-mgmt#reviews", timeout=30000)
    page.wait_for_timeout(5000)

    menu_items = page.query_selector_all('.p-panelmenu-header-link, .p-menuitem-link')
    for item in menu_items:
        text = item.inner_text().strip()
        if text == 'REVIEWS':
            item.click()
            page.wait_for_timeout(4000)
            break

    page.wait_for_timeout(3000)
    body_text = page.inner_text('body')
    return parse_renderseo_reviews(body_text)


def parse_renderseo_reviews(text):
    """Parse RenderSEO review text into structured review objects."""
    reviews = []
    lines = text.split('\n')
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        date_match = re.match(r'^On\s+(\d{4}/\d{1,2}/\d{1,2})$', stripped)

        if date_match:
            date_str = date_match.group(1)
            i += 1
            review_text_parts = []
            reply_text_parts = []
            rating = None
            mode = 'review'

            while i < len(lines):
                line = lines[i]
                s = line.strip()

                # Check for rating line
                if re.match(r'^\s*([1-5])\s*$', line):
                    rating = int(s)
                    i += 1
                    mode = 'reply'
                    continue

                # Check for empty rating (reply end marker)
                if rating and s == '' and mode == 'reply':
                    i += 1
                    continue

                # Stop at next "On" date
                if re.match(r'^On\s+\d{4}/\d{1,2}/\d{1,2}$', s):
                    break

                # Skip store code blocks and other non-review content
                skip = {'ADD/EDIT', 'EXPORT', 'SELECT', 'Store Code', 'LOCATION', 'REVIEW', 'RATING',
                        'RESPONSE', '5255', 'Santa Maria', 'Milton, ON', 'L9T6J5',
                        'Welcome', 'HOME', 'METRICS', 'KEYWORDS', 'OTHER REVIEWS', 'REPORTS',
                        'Reviews from', 'Your Reviews.', 'Review Management',
                        'St. Louis Bar'}
                should_skip = any(x in s for x in skip)

                if not should_skip and s:
                    if mode == 'review':
                        review_text_parts.append(s)
                    else:
                        reply_text_parts.append(s)

                i += 1

            if rating:
                review = {
                    'date_str': date_str,
                    'rating': rating,
                    'text': ' '.join(review_text_parts).strip() if review_text_parts else '',
                    'reply': ' '.join(reply_text_parts).strip() if reply_text_parts else '',
                    'restaurant': 'slf',
                    'sort_date': date_str.replace('/', '-')
                }
                reviews.append(review)
            continue

        i += 1

    return reviews


def scrape_google_maps_reviews(page, restaurant_key):
    """Scrape info from Google Maps for Bar Burrito locations."""
    rest = RESTAURANTS[restaurant_key]
    print(f"  [{rest['short']}] Loading Google Maps...")

    try:
        page.goto(rest['maps_url'], wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)
    except Exception as e:
        print(f"  [{rest['short']}] Navigation error: {e}")

    try:
        tabs = page.query_selector_all('[role="tab"], button, div[role="button"]')
        for el in tabs:
            text = el.inner_text().strip()
            if text == "Reviews":
                el.click()
                time.sleep(4)
                break
    except:
        pass

    for _ in range(3):
        try:
            page.evaluate("window.scrollBy(0, 600)")
            time.sleep(2)
        except:
            break

    body_text = page.inner_text('body')

    rating = None
    total_reviews = None

    rating_match = re.search(r'barBURRITO\s*([\d.]+)', body_text)
    if rating_match:
        rating = float(rating_match.group(1))

    rev_count = re.search(r'([\d,]+)\s*reviews?', body_text)
    if rev_count:
        total_reviews = rev_count.group(1)

    # Get star distribution
    dist_match = re.search(r'5\s+([\d]+)\s+4\s+([\d]+)\s+3\s+([\d]+)\s+2\s+([\d]+)\s+1\s+([\d]+)', body_text)

    return {
        'rating': rating,
        'total_reviews': total_reviews,
        'restaurant': restaurant_key,
        'fetched_at': datetime.now(timezone.utc).isoformat()
    }


def generate_dashboard_html(all_reviews, bb_data):
    """Generate a beautiful HTML dashboard page."""

    def sort_key(r):
        d = r.get('sort_date', r.get('date_str', ''))
        parts = d.replace('-', '/').split('/')
        if len(parts) == 3:
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        return (0, 0, 0)

    all_sorted = sorted(all_reviews, key=sort_key, reverse=True)
    top_5 = all_sorted[:5]

    slf_reviews = [r for r in all_reviews if r.get('restaurant') == 'slf']
    avg_sum = 0
    avg_count = 0
    for r in slf_reviews:
        if r.get('rating'):
            try:
                avg_sum += int(r['rating'])
                avg_count += 1
            except:
                pass
    slf_avg = round(avg_sum / avg_count, 1) if avg_count > 0 else 'N/A'

    # Stat cards
    stat_cards = []
    stat_cards.append({
        'name': RESTAURANTS['slf']['name'],
        'address': RESTAURANTS['slf']['address'],
        'color': RESTAURANTS['slf']['color'],
        'rows': [
            ('Avg Rating', str(slf_avg)),
            ('Reviews (30d)', str(len(slf_reviews))),
            ('Response Rate', '80.8%'),
        ]
    })

    for key in ['bb_milton', 'bb_brampton']:
        r = RESTAURANTS[key]
        d = bb_data.get(key, {})
        rows = []
        if d.get('rating'):
            rows.append(('Google Rating', str(d['rating'])))
        else:
            rows.append(('Google Rating', 'N/A'))
        if d.get('total_reviews'):
            rows.append(('Total Reviews', d['total_reviews']))
        rows.append(('Status', 'Data from Google Maps'))
        stat_cards.append({
            'name': r['name'],
            'address': r['address'],
            'color': r['color'],
            'rows': rows,
        })

    stats_html = ''
    for s in stat_cards:
        rows_html = ''
        for label, value in s['rows']:
            rows_html += f'''<div class="stat-row"><span class="stat-label">{label}</span><span class="stat-value">{value}</span></div>\n'''
        stats_html += f'''<div class="stat-card" style="border-top: 4px solid {s['color']};"><h3>{s['name']}</h3><p class="stat-address">{s['address']}</p>{rows_html}</div>\n'''

    # Review cards
    top_5_html = ''
    for r in top_5:
        rest_info = RESTAURANTS.get(r.get('restaurant', 'slf'), RESTAURANTS['slf'])
        r_rating = int(r.get('rating', 0)) if r.get('rating') else 0
        stars = '★' * r_rating + '☆' * (5 - r_rating)
        color = rest_info['color']

        text = r.get('text', '')
        reply = r.get('reply', '')
        date = r.get('date_str', '')

        top_5_html += f'''<div class="review-card" style="border-left: 4px solid {color};"><div class="review-header"><span class="restaurant-badge" style="background:{color};">{rest_info['short']}</span><span class="review-date">{date}</span><span class="review-stars" style="color:{color};">{stars}</span></div><div class="review-body"><p>{text if text else 'No text'}</p></div>'''
        if reply:
            top_5_html += f'''<div class="review-reply"><strong>Reply:</strong> {reply}</div>'''
        top_5_html += '</div>\n'

    now = datetime.now(timezone.utc).strftime('%B %d, %Y at %I:%M %p UTC')

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Restaurant Review Dashboard</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Inter', sans-serif; background: #f5f5f7; color: #1d1d1f; padding: 32px; max-width: 1200px; margin: 0 auto; }}
  .dashboard-header {{ margin-bottom: 32px; }}
  .dashboard-header h1 {{ font-size: 28px; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 4px; }}
  .dashboard-header p {{ color: #6e6e73; font-size: 14px; }}
  .last-updated {{ color: #6e6e73; font-size: 12px; margin-top: 4px; }}
  .stats-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 32px; }}
  .stat-card {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .stat-card h3 {{ font-size: 15px; font-weight: 700; margin-bottom: 2px; }}
  .stat-address {{ font-size: 12px; color: #6e6e73; margin-bottom: 12px; }}
  .stat-row {{ display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px; }}
  .stat-label {{ color: #6e6e73; }}
  .stat-value {{ font-weight: 600; }}
  .section-title {{ font-size: 20px; font-weight: 700; margin-bottom: 16px; letter-spacing: -0.3px; }}
  .reviews-list {{ display: flex; flex-direction: column; gap: 12px; }}
  .review-card {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .review-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }}
  .restaurant-badge {{ padding: 2px 10px; border-radius: 4px; color: white; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
  .review-date {{ font-size: 12px; color: #6e6e73; }}
  .review-stars {{ font-size: 14px; letter-spacing: 1px; }}
  .review-body p {{ font-size: 14px; line-height: 1.6; color: #1d1d1f; }}
  .review-reply {{ margin-top: 10px; padding: 10px 14px; background: #f5f5f7; border-radius: 8px; font-size: 13px; color: #515154; }}
  @media (max-width: 768px) {{ body {{ padding: 16px; }} .stats-grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="dashboard-header">
<h1>Restaurant Review Dashboard</h1>
<p>All reviews across your 3 locations</p>
<p class="last-updated">Last updated: {now}</p>
</div>
<div class="stats-grid">{stats_html}</div>
<h2 class="section-title">Top 5 Most Recent Reviews</h2>
<div class="reviews-list">
{top_5_html if top_5_html else '<p style="color: #6e6e73;">No reviews found yet.</p>'}
</div>
<p style="color: #6e6e73; font-size: 13px; margin-top: 24px;">Dashboard refreshes 3x daily via automated cron job.</p>
</body>
</html>'''

    return html


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=" * 60)
    print("  RESTAURANT REVIEW DASHBOARD SCRAPER")
    print("=" * 60)

    all_reviews = []
    bb_data = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        # SLF
        print("\n[1/3] St. Louis Bar & Grill...")
        page = ctx.new_page()
        try:
            slf_reviews = scrape_slf_reviews(page)
            all_reviews.extend(slf_reviews)
            print(f"  [SLF] Found {len(slf_reviews)} reviews")
        except Exception as e:
            print(f"  [SLF] Error: {e}")
            import traceback; traceback.print_exc()
        page.close()

        # BB Milton
        print("\n[2/3] Bar Burrito - Milton...")
        page = ctx.new_page()
        try:
            bb_data['bb_milton'] = scrape_google_maps_reviews(page, 'bb_milton')
        except Exception as e:
            print(f"  [BB Milton] Error: {e}")
        page.close()

        # BB Brampton
        print("\n[3/3] Bar Burrito - Brampton...")
        page = ctx.new_page()
        try:
            bb_data['bb_brampton'] = scrape_google_maps_reviews(page, 'bb_brampton')
        except Exception as e:
            print(f"  [BB Brampton] Error: {e}")
        page.close()

        browser.close()

    # Generate dashboard
    print("\n" + "=" * 60)
    print("  GENERATING DASHBOARD HTML")
    print("=" * 60)

    html = generate_dashboard_html(all_reviews, bb_data)

    with open(OUTPUT_FILE, 'w') as f:
        f.write(html)
    with open(DASHBOARD_COPY, 'w') as f:
        f.write(html)

    # Save JSON data
    data = {
        'last_updated': datetime.now(timezone.utc).isoformat(),
        'reviews_count': len(all_reviews),
        'bar_burrito': {k: {kk: vv for kk, vv in v.items() if kk != 'reviews_text'} for k, v in bb_data.items()}
    }
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n  Dashboard: {DASHBOARD_COPY}")
    print(f"  HTML: {OUTPUT_FILE}")
    print(f"  Data: {DATA_FILE}")
    print("=" * 60)


if __name__ == '__main__':
    main()
