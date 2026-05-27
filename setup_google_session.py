#!/usr/bin/env python3
"""
One-time setup: Sign into Google to enable full Google Maps review access.
After this runs once, all future dashboard runs will use the saved session.

Run: python3 setup_google_session.py

A CloakBrowser window will open. Sign into your Google account
and approve 2FA on your phone. The session is saved automatically.
"""
import os, json, time

SESSION_FILE = os.path.join(os.path.dirname(__file__), "google_maps_session.json")

def main():
    print("=" * 60)
    print("  GOOGLE MAPS SESSION SETUP")
    print("=" * 60)
    print()
    print("This will open a CloakBrowser window.")
    print("1. You'll see the Google Maps sign-in page")
    print("2. Sign in with your Google account")
    print("3. Approve the 2FA prompt on your phone")
    print("4. The window will close once the session is saved")
    print()

    try:
        from cloakbrowser import launch
    except ImportError:
        print("CloakBrowser not installed. Installing...")
        import subprocess
        subprocess.run(["pip", "install", "cloakbrowser"], check=True)
        from cloakbrowser import launch

    browser = launch(
        headless=False,  # Must be visible for you to sign in
        stealth_args=True,
        timezone="America/Toronto",
        locale="en-US",
        humanize=True,
        human_preset="default",
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        locale="en-US",
        timezone_id="America/Toronto",
    )
    page = context.new_page()

    # Navigate to Google Maps
    page.goto("https://www.google.com/maps", wait_until="domcontentloaded")
    time.sleep(3)

    # Look for sign-in button
    try:
        signin_btn = page.locator('a:has-text("Sign in"), button:has-text("Sign in")')
        if signin_btn.is_visible(timeout=5000):
            print("\nClicking Sign in button...")
            signin_btn.click()
            time.sleep(3)
    except:
        print("\nAlready signed in or no sign-in button found")

    print("\n=== PLEASE SIGN IN NOW ===")
    print("The browser window is open. Sign into your Google account.")
    print("Approve the 2FA prompt on your phone if asked.")
    print()
    print("Waiting up to 3 minutes for you to sign in...")

    # Wait for user to sign in (check for navigation away from login page)
    for i in range(90):
        time.sleep(2)
        current_url = page.evaluate("window.location.href")
        try:
            body = page.inner_text("body")
            if "Sign in" not in body and "sign in" not in body.lower():
                print(f"\nYou appear to be signed in! (detected at ~{i*2}s)")
                break
        except:
            pass
        if i % 10 == 0:
            print(f"  Still waiting... ({i*2}s)")

    # Save full session state
    print("\nSaving session state...")

    # Save cookies
    cookies = context.cookies()

    # Save localStorage and sessionStorage
    storage = page.evaluate("""() => {
        const data = {local: {}, session: {}};
        for (let i = 0; i < localStorage.length; i++) {
            const k = localStorage.key(i);
            data.local[k] = localStorage.getItem(k);
        }
        for (let i = 0; i < sessionStorage.length; i++) {
            const k = sessionStorage.key(i);
            data.session[k] = sessionStorage.getItem(k);
        }
        return data;
    }""")

    session_data = {
        "cookies": cookies,
        "storage": storage,
        "user_agent": page.evaluate("navigator.userAgent"),
    }

    with open(SESSION_FILE, "w") as f:
        json.dump(session_data, f, indent=2)

    print(f"  Session saved to: {SESSION_FILE}")
    print(f"  Cookies: {len(cookies)}")
    print(f"  Storage keys: {len(storage.get('local', {}))} local, {len(storage.get('session', {}))} session")
    print()
    print("Done! Future dashboard runs will automatically use this session.")
    print()

    browser.close()

if __name__ == "__main__":
    main()
