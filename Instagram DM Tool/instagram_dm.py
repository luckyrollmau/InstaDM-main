from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pickle
from selenium.common.exceptions import NoSuchElementException

# Set Chrome options
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Initialize WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
driver.get("https://www.instagram.com")
time.sleep(2)

# Load cookies to stay logged in
try:
    with open("session.pkl", "rb") as file:
        cookies = pickle.load(file)
        for cookie in cookies:
            driver.add_cookie(cookie)
    driver.refresh()
    time.sleep(2)
except FileNotFoundError:
    print("No saved session found. Please log in manually and save the session.")

def locate_element_with_fallback(driver, xpaths):
    """Locate an element by trying multiple fallback XPaths."""
    for xpath in xpaths:
        try:
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath)))
            print(f"Element found using XPath: {xpath}")
            return element
        except NoSuchElementException:
            print(f"Element not found with XPath: {xpath}")
            continue
    raise Exception("Element could not be located with any known XPaths.")

try:
    # Go to Direct Messages inbox
    driver.get("https://www.instagram.com/direct/inbox/")
    time.sleep(5)

    # Dismiss the "Turn on Notifications" popup if it appears
    try:
        not_now_button = locate_element_with_fallback(driver, [
            "//button[text()='Not Now']",
            "//button[contains(@class, 'HoLwm')]",
        ])
        not_now_button.click()
        time.sleep(2)
    except Exception as e:
        print("No 'Turn on Notifications' popup appeared or could not be clicked.")

    # Navigate to the "New Message" page
    driver.get("https://www.instagram.com/direct/new/")
    time.sleep(5)

    # Click the "Send message" button using multiple possible selectors
    try:
        send_message_button = locate_element_with_fallback(driver, [
            "//div[@role='button' and text()='Send message']",
            "//button[contains(text(), 'Send message')]",
            "//div[contains(@class, 'x1ey2m1c') and contains(@role, 'button')]"
        ])
        send_message_button.click()
        time.sleep(2)
    except Exception as e:
        print(f"Could not locate the 'Send message' button. Error: {e}")
        driver.quit()
        exit()

    # Search for user and select the first result
    instagram_username = "timeismau"  # Replace with the username you want to message
    try:
        recipient_input = locate_element_with_fallback(driver, ["//input[@name='queryBox']", "//input[@placeholder='Search...']"])
        recipient_input.send_keys(instagram_username)
        time.sleep(3)

        # Select the first dropdown item (user) in search results
        first_result = locate_element_with_fallback(driver, ["(//div[@role='none'])[1]", "//div[@class='-qQT3']"])
        driver.execute_script("arguments[0].scrollIntoView(true);", first_result)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", first_result)
        time.sleep(2)
    except Exception as e:
        print(f"Error selecting the first search result: {e}")
        driver.quit()
        exit()

    # Click "Message" button to open chat window
    try:
        message_button = locate_element_with_fallback(driver, [
            "//div[text()='Message' or text()='Chat']",
            "//button[contains(@class, 'sqdOP')]"
        ])
        message_button.click()
        time.sleep(5)  # Allow extra time for the chat window to load
    except Exception as e:
        print(f"Error clicking the 'Message' button: {e}")
        driver.quit()
        exit()

    # Locate message box with multiple fallback XPaths and send the message
    try:
        message_box = locate_element_with_fallback(driver, [
            "//p[contains(@class, 'xat24cr') and contains(@class, 'xdj266')]",
            "//p[@role='textbox']",
            "//div[@contenteditable='true']",
            "//textarea[contains(@placeholder, 'Message')]",
            "//input[@type='text']"
        ])
        message_box.click()
        message_box.send_keys("yo,wyd?")
        message_box.send_keys(Keys.RETURN)
    except Exception as e:
        print(f"Error entering the message: {e}")
        driver.quit()
        exit()

except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    # Close the browser after a delay
    time.sleep(5)
    driver.quit()
