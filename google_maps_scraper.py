#!/usr/bin/env python3
"""
Google Maps review scraper using saved session.
Uses CloakBrowser with a persistent Google session to access full review data.
"""
import os, json, time, re

SESSION_FILE = os.path.join(os.path.dirname(__file__), "google_maps_session.json")

def scrape_location_reviews(browser, maps_url, max_reviews=20):
    """Scrape reviews from Google Maps for a given location."""
    print(f"  Loading Google Maps page...")

    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="America/Toronto",
    )

    # Restore session if available
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE) as f:
            session = json.load(f)
        context.add_cookies(session.get("cookies", []))
        print(f"  Restored {len(session.get('cookies', []))} cookies from saved session")

    page = context.new_page()

    try:
        page.goto(maps_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)
    except Exception as e:
        print(f"  Navigation error: {e}")

    # Click Reviews tab
    try:
        tabs = page.query_selector_all('[role="tab"], button, div[role="button"]')
        for el in tabs:
            text = el.inner_text().strip()
            if text == "Reviews":
                el.click()
                time.sleep(3)
                break
    except:
        pass

    # Scroll to load more reviews
    for _ in range(10):
        try:
            page.evaluate("window.scrollBy(0, 1000)")
            time.sleep(1.5)
        except:
            break

    # Extract rating and total
    body = page.inner_text("body")

    # Try to get structured review data
    reviews = []

    # Method 1: Extract from page JS data
    try:
        raw = page.evaluate("""() => {
            const scripts = document.querySelectorAll('script[nonce]');
            for (let s of scripts) {
                const t = s.textContent || '';
                if (t.includes('rating') && t.includes('review') && t.includes('author_name')) {
                    return t.substring(0, 10000);
                }
            }
            return null;
        }""")
        if raw:
            matches = re.findall(r'"author_name":"([^"]+)"[^}]+"rating":(\d)[^}]+"relative_time_description":"([^"]+)"[^}]+"text":"([^"]+)"', raw)
            for m in matches:
                reviews.append({
                    'name': m[0],
                    'rating': int(m[1]),
                    'time_ago': m[2],
                    'text': m[3],
                })
    except:
        pass

    # Method 2: Parse from visible text (fallback)
    if not reviews:
        lines = body.split('\n')
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            time_match = re.match(r'^(\d+)\s+(month|months|day|days|week|weeks|year|years|hour|hours)\s+ago$', stripped.lower())
            if time_match and i + 1 < len(lines):
                time_ago = f"{time_match.group(1)} {time_match.group(2)} ago"
                name = ""
                for j in range(max(0, i-3), i):
                    if lines[j].strip() and not lines[j].strip().isdigit():
                        name = lines[j].strip()
                        break
                review_text = ""
                j = i + 1
                while j < len(lines) and j < i + 6:
                    if lines[j].strip():
                        review_text += " " + lines[j].strip()
                    j += 1
                if len(review_text.strip()) > 10:
                    reviews.append({
                        'name': name,
                        'time_ago': time_ago,
                        'text': review_text.strip(),
                        'rating': None,
                    })
                i = j
                continue
            i += 1

    # Extract overall rating
    rating = None
    match = re.search(r'(\d+\.\d+)\s*\(([\d,]+)\s+reviews?\)', body)
    if match:
        rating = float(match.group(1))
        total = match.group(2)
    else:
        match = re.search(r'([\d.]+)\s*\n', body)
        if match:
            try:
                rating = float(match.group(1))
            except:
                pass
        total = None

    page.close()
    context.close()

    return {
        'rating': rating,
        'total_reviews': total,
        'reviews': reviews[:max_reviews],
        'fetched_at': time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
