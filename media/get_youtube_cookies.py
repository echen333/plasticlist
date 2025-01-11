from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import os

def get_cookies():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--headless")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    driver.get("https://www.youtube.com")
    time.sleep(5)  # Let the page load and set cookies

    # Save cookies to file
    with open("youtube_cookies.txt", "w") as f:
        for cookie in driver.get_cookies():
            f.write(f"{cookie['domain']}\tTRUE\t{cookie['path']}\t{cookie['secure']}\t{cookie.get('expiry', 0)}\t{cookie['name']}\t{cookie['value']}\n")

    driver.quit()

if __name__ == "__main__":
    get_cookies()
