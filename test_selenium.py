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
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    try:
        driver.get("https://nepsealpha.com/nepse-chart")
        print("📄 Page loaded")

        # Step 1: Click the first button
        try:
            print("⏳ Waiting for first button...")
            first_button = wait.until(EC.presence_of_element_located((
                By.XPATH,
                '//*[@id="app"]/div[1]/div[1]/div[3]/div/div/div/div/div[1]/button'
            )))
            driver.execute_script("arguments[0].click();", first_button)
            print("✅ First button clicked (JS)")
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
            time.sleep(2)
        except Exception:
            print("❌ Failed to click 'Broker Picks' span")
            traceback.print_exc()

        # Step 4: Wait for data table and extract rows
        try:
            print("⏳ Waiting for table to appear...")
            table = wait.until(EC.presence_of_element_located((
                By.XPATH,
                '//*[@id="app"]/div[1]/div[1]/div[3]/div/div[1]/div/div/div[2]/div/div[2]/div/div/table'
            )))
            driver.execute_script("arguments[0].scrollIntoView(true);", table)
            time.sleep(1)

            # Ensure data is loaded (not "No data available")
            try:
                wait.until_not(EC.text_to_be_present_in_element(
                    (By.XPATH, '//table'), "No data available"
                ))

                # Collect actual data rows
                rows = wait.until(EC.presence_of_all_elements_located((
                    By.XPATH,
                    '//table//tbody/tr'
                )))
                print(f"\n✅ Real data rows detected: {len(rows)}\n")
                for row in rows:
                    print(row.text)
            except TimeoutException:
                print("❌ Data rows did not load in time.")
        except Exception:
            print("❌ Failed to find or extract table")
            traceback.print_exc()

    finally:
        driver.quit()

if __name__ == "__main__":
    run_headless_chrome()
