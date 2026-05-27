# Restaurant Review Dashboard

A free, open-source dashboard that aggregates Google reviews across multiple restaurant locations. Generates a clean HTML dashboard with the top 5 most recent reviews and per-location stats.

## Features

- **Multi-location support** — Monitor reviews across all your restaurants
- **Top 5 recent reviews** — See the most important feedback at a glance
- **Per-location stats** — Average rating, total reviews, response rate
- **Auto-refresh** — Cron-based scheduling (3x daily)
- **Google Maps integration** — Fetches reviews directly from Google Maps (no API key needed)
- **RenderSEO integration** — For locations with a RenderSEO account (full review text, replies)
- **Clean HTML dashboard** — Stripe-style design, responsive, openable in any browser

## Supported Sources

| Source | Requirements | Data Available |
|--------|-------------|----------------|
| RenderSEO | Account credentials | Full review text, ratings, dates, business replies |
| Google Maps | Google account session (free) | Ratings, review counts, detailed review text |

## Prerequisites

- Python 3.10+
- Playwright (`pip install playwright && playwright install chromium`)
- _Optional:_ CloakBrowser for bypassing Google automation detection

## Quick Start

1. **Clone the repo:**
   ```bash
   git clone https://github.com/yourusername/restaurant-review-dashboard.git
   cd restaurant-review-dashboard
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. **Configure your restaurants:**
   Edit `restaurants.json` with your locations:
   ```json
   {
     "restaurants": [
       {
         "id": "slf",
         "name": "St. Louis Bar & Grill",
         "address": "Unit 8, 604 Santa Maria Blvd, Milton, ON",
         "source": "renderseo",
         "renderseo_email": "your@email.com",
         "renderseo_password": "your-password"
       },
       {
         "id": "bb_milton",
         "name": "Bar Burrito - Milton",
         "address": "Unit 7, 604 Santa Maria Blvd, Milton, ON",
         "source": "google_maps",
         "maps_url": "https://www.google.com/maps/place/..."
       }
     ]
   }
   ```

4. **Run the scraper:**
   ```bash
   python3 review_dashboard.py
   ```

5. **Open the dashboard:**
   ```
   open restaurant_review_dashboard.html
   ```

## Google Maps Session (Free Review Access)

Google Maps limits review visibility for anonymous users. To get full review text:

1. Run the session setup script:
   ```bash
   python3 setup_google_session.py
   ```
2. A CloakBrowser window opens. Sign into your Google account.
3. Approve the 2FA prompt on your phone.
4. The session is saved. Future runs automatically use it.

This is a **one-time setup** — no API keys or paid services required.

## Configuration

### Adding a RenderSEO location
Fill in the RenderSEO email/password in `restaurants.json`.

### Adding a Google Maps location
1. Search the location on Google Maps
2. Copy the URL from your browser's address bar
3. Add it to `restaurants.json` as `maps_url`

### Scheduling (Cron)
```bash
# Runs at 7 AM, 2 PM, and 9 PM daily
0 7,14,21 * * * cd /path/to/repo && python3 review_dashboard.py
```

## How It Works

1. **Scraper** uses Playwright (or CloakBrowser) to navigate review sources
2. **Parser** extracts structured review data (date, rating, text, reply)
3. **Dashboard generator** builds a styled HTML page
4. **Cron job** runs the pipeline on schedule

## License

MIT — Free to use, modify, and share.
