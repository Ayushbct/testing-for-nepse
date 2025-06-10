from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def run_headless_chrome():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://nepsealpha.com/nepse-chart")
        wait = WebDriverWait(driver, 20)

        # 1. Click the first button
        first_button = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            '//*[@id="app"]/div[1]/div[1]/div[3]/div/div/div/div/div[1]/button'
        )))
        first_button.click()
        print("✅ First button clicked")

        # 2. Click 'PRIME PICKS' button
        prime_picks_button = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            '//*[@id="app"]/div[1]/div[1]/div[3]/div/div[1]/div/div/div[2]/button[3][span[text()="PRIME PICKS"]]'
        )))
        prime_picks_button.click()
        print("✅ 'PRIME PICKS' button clicked")

        # 3. Click 'Broker Picks' span
        broker_picks_span = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            '//*[@id="app"]/div[1]/div[1]/div[3]/div/div[1]/div/div/div[2]/div[2]/div/span[9]/span[text()="Broker Picks"]'
        )))
        broker_picks_span.click()
        print("✅ 'Broker Picks' span clicked")

        # 4. Wait for the table and print its text content
        table = wait.until(EC.presence_of_element_located((
            By.XPATH,
            '//*[@id="app"]/div[1]/div[1]/div[3]/div/div[1]/div/div/div[2]/div/div[2]/div/div/table'
        )))
        print("\n📋 Table content:\n")
        print(table.text)

    except Exception as e:
        print("❌ Error:", e)
    finally:
        driver.quit()

if __name__ == "__main__":
    run_headless_chrome()
