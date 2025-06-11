from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Show browser for manual CAPTCHA if needed
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("🔐 Opening site...")
        page.goto("https://nepsealpha.com/nepse-chart", wait_until="load")
        page.wait_for_timeout(7000)  # wait for Cloudflare challenge

        # Click "Verify you're human" if it's visible
        page.screenshot(path="cloudflare.png")
        try:
            verify_button = page.locator("text=Verify you are human")
            if verify_button.is_visible():
                print("🧠 Clicking 'Verify you are human' button...")
                verify_button.click()
                page.wait_for_timeout(5000)
                page.screenshot(path="button_clicked.png")
            else:
                print("✅ No verification needed.")
        except Exception as e:
            print("⚠️ Couldn't find 'Verify' button:", str(e))

        # Continue to load the Prime Picks
        page.locator("text=Prime Picks").click()
        page.locator("text=Broker Picks").click()
        page.wait_for_timeout(3000)

        rows = page.locator("table tbody tr").all()
        print(f"\n📊 Found {len(rows)} rows:\n")
        for row in rows:
            print(" | ".join(row.inner_text().split("\n")))

        browser.close()

if __name__ == "__main__":
    main()
