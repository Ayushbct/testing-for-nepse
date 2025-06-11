from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import traceback

def run_headless_chrome():
    options = Options()
    options.add_argument("--headless=new")  # Headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """
})

    wait = WebDriverWait(driver, 20)
    
    try:
        driver.get("https://nepsealpha.com/nepse-chart")
        print("📄 Page loaded")
        driver.save_screenshot('step0.png')

        # Step 1: Click the first button
        try:
            print("⏳ Waiting for first button...")
            first_button = wait.until(EC.presence_of_element_located((
                By.XPATH,
                '//*[@id="app"]/div[1]/div[1]/div[3]/div/div/div/div/div[1]/button'
            )))
            driver.execute_script("arguments[0].click();", first_button)
            print("✅ First button clicked (JS)")
            driver.save_screenshot('step1.png')
            time.sleep(2)
        except Exception:
            print("❌ Failed to click first button")
            traceback.print_exc()

        # Step 2: Click the "Prime Picks" button
        try:
            print("⏳ Waiting for 'Prime Picks' button...")
            prime_picks_button = wait.until(EC.presence_of_element_located((
                By.XPATH,
                "//button[contains(@class, 'v-btn') and span[text()[normalize-space()='Prime Picks']]]"
            )))
            driver.execute_script("arguments[0].click();", prime_picks_button)
            print("✅ 'Prime Picks' button clicked (JS)")
            driver.save_screenshot('step2.png')
            time.sleep(2)
        except Exception:
            print("❌ Failed to click 'Prime Picks' button")
            traceback.print_exc()

        # Step 3: Click the "Broker Picks" span
        try:
            print("⏳ Waiting for 'Broker Picks' span...")
            broker_picks_span = wait.until(EC.presence_of_element_located((
                By.XPATH,
                '//span[normalize-space(text())="Broker Picks"]'
            )))
            driver.execute_script("arguments[0].scrollIntoView(true);", broker_picks_span)
            driver.execute_script("arguments[0].click();", broker_picks_span)
            print("✅ 'Broker Picks' span clicked (JS)")
            driver.save_screenshot('step3.png')
            time.sleep(3)  # increased wait to give time for data load
        except Exception:
            print("❌ Failed to click 'Broker Picks' span")
            traceback.print_exc()

        # Step 4: Extract table rows after page updates (no sorting)
        try:
            print("⏳ Waiting for data rows to appear...")
            # Instead of waiting for "No data" to disappear, wait for rows that have actual data cells
            rows = WebDriverWait(driver, 20).until(lambda d: d.find_elements(
                By.XPATH,
                '//table//tbody/tr[td and normalize-space(string-length(.)) > 0]'
            ))
            driver.save_screenshot('step4.png')
            # If no rows found, print a message
            if not rows:
                print("❌ No data rows found")
            else:
                print(f"\n✅ Found {len(rows)} data rows:\n")
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    print(" | ".join([cell.text.strip() for cell in cells if cell.text.strip() != ""]))
        except TimeoutException:
            print("❌ Timeout: Data rows did not appear")
        except Exception:
            print("❌ Failed to extract rows")
            traceback.print_exc()

    finally:
        driver.quit()

if __name__ == "__main__":
    run_headless_chrome()
