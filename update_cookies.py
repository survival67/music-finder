import os
import pickle
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

COOKIES_PKL = "cookies.pkl"
COOKIES_TXT = "cookies.txt"
YOUTUBE_URL = "https://www.youtube.com"

def save_cookies_txt(cookies, path):
    with open(path, "w", encoding="utf-8") as f:
        for cookie in cookies:
            if "name" in cookie and "value" in cookie:
                f.write(f"{cookie['name']}\t{cookie['value']}\n")

def update_cookies(first_login=False):
    options = Options()
    if not first_login:
        options.add_argument("--headless=new")  # фоновий режим після першого входу
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get(YOUTUBE_URL)
    time.sleep(5)

    if os.path.exists(COOKIES_PKL) and not first_login:
        with open(COOKIES_PKL, "rb") as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    pass
        driver.get(YOUTUBE_URL)
        time.sleep(5)

    cookies = driver.get_cookies()
    with open(COOKIES_PKL, "wb") as f:
        pickle.dump(cookies, f)
    save_cookies_txt(cookies, COOKIES_TXT)

    driver.quit()
    print("✅ Cookies збережно!")

if __name__ == "__main__":
    if not os.path.exists(COOKIES_PKL):
        print("⚠️ Файли cookies не знайдено. Відкрийте браузер та увійдіть.")
        update_cookies(first_login=True)
    else:
        update_cookies(first_login=False)
