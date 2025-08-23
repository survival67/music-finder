import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

COOKIES_FILE = "cookies.txt"

def save_cookies_netscape(driver, path="cookies.txt"):
    cookies = driver.get_cookies()
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP Cookie File\n")
        for c in cookies:
            domain = c.get("domain", "")
            include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
            path_c = c.get("path", "/")
            secure = "TRUE" if c.get("secure") else "FALSE"
            expiry = int(c.get("expiry", 0)) if c.get("expiry") else 0
            name = c.get("name", "")
            value = c.get("value", "")
            line = f"{domain}\t{include_subdomains}\t{path_c}\t{secure}\t{expiry}\t{name}\t{value}\n"
            f.write(line)
    print(f"✅ Cookies збережено в {path} у форматі Netscape")

def main():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get("https://www.youtube.com/")
    time.sleep(5)

    print("🔑 Авторизуйся на YouTube у відкритому вікні.")
    input("Вкінці натисни Enter...")

    save_cookies_netscape(driver)
    driver.quit()

if __name__ == "__main__":
    main()