from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time
import pickle

# Set Chrome options
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Initialize WebDriver with Service
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# Open Instagram
driver.get("https://www.instagram.com")
time.sleep(2)

# Log in (replace 'your_username' and 'your_password' with your actual login details)
username = driver.find_element("name", "username")
password = driver.find_element("name", "password")
username.send_keys("luckyrollmau")
password.send_keys("B00m3rang189@")
password.send_keys(Keys.RETURN)

# Wait for user input to proceed (enter the 2FA code manually in the browser)
input("Please complete the 2FA verification in the browser, then press Enter here to continue...")

# Save the session for Part 2
with open("session.pkl", "wb") as file:
    pickle.dump(driver.get_cookies(), file)

print("Login complete. Session saved.")
driver.quit()
