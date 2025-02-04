from flask import Flask, render_template, request, redirect, url_for, jsonify
import csv
import time
import os
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pickle
from selenium.common.exceptions import NoSuchElementException

# Add these imports at the top of your file
from datetime import datetime
import json



# Add these constants
HISTORY_FILE = "message_history.json"
CURRENT_STATUS = {"current": 0, "total": 0, "messages": []}


def load_message_history():
    """Load the message history for the current logged-in account."""
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_to_history(username, target_username, status, message_text):
    """Save message attempt to history."""
    history = load_message_history()
    
    if username not in history:
        history[username] = []
    
    history[username].append({
        "target_username": target_username,
        "status": status,
        "message": message_text,
        "timestamp": datetime.now().isoformat()
    })
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def check_if_messaged(username, target_username):
    """Check if a target user has already been messaged by this account."""
    history = load_message_history()
    if username in history:
        return any(msg["target_username"] == target_username for msg in history[username])
    return False



# Define the login_and_save_session function
def login_and_save_session(username, password):
    """Login and save the session cookies to a file."""
    driver = initialize_driver()  # Use your existing driver setup
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(2)

    # Locate and fill the login form
    driver.find_element(By.NAME, "username").send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    
    time.sleep(60)  # Wait for the login process to complete
    
    # Save cookies to a session file
    cookies = driver.get_cookies()
    with open(SESSION_FILE, "wb") as file:
        pickle.dump(cookies, file)
    
    print("Session saved successfully!")
    driver.quit()



def load_sent_usernames():
    """Load previously sent usernames from the log file to avoid duplicate messages."""
    sent_usernames = set()
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as log_file:
            log_reader = csv.reader(log_file)
            next(log_reader)  # Skip header
            for log_row in log_reader:
                sent_usernames.add(log_row[1])  # Collect usernames that have already been messaged
    return sent_usernames

def log_to_csv(log_file, data):
    """Log each message attempt to CSV."""
    with open(log_file, "a", newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(data)


app = Flask(__name__)

SESSION_FILE = "session.pkl"

# Set Chrome options to run in headless mode
def get_chrome_path():
    """Check if Chrome path is set in the environment variable or use a default."""
    chrome_path = os.getenv("CHROME_PATH")
    
    if not chrome_path:
        # If CHROME_PATH is not set, try default locations
        if os.name == 'nt':  # Windows
            chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        elif os.name == 'posix':  # macOS/Linux
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        
        if not os.path.exists(chrome_path):
            raise Exception("Chrome executable not found. Please set the CHROME_PATH environment variable or provide the correct path.")
    
    return chrome_path


def initialize_driver():
    """Initialize the Chrome WebDriver in headless mode, with optional custom Chrome path."""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--headless")  # Ensure headless mode is enabled
    chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
    chrome_options.add_argument("--window-size=1920x1080")  # Set window size (important for some websites)

    # Debugging: Confirm headless mode is set
    if "--headless" in chrome_options.arguments:
        print("Headless mode is enabled.")
    else:
        print("Headless mode is NOT enabled.")

    # Get the correct Chrome path from environment variable or default
    chrome_path = get_chrome_path()
    chrome_options.binary_location = chrome_path  # Set custom Chrome path

    # Use webdriver_manager to handle ChromeDriver installation
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver


def locate_element_with_fallback(driver, xpaths):
    """Locate an element by trying multiple fallback XPaths."""
    for xpath in xpaths:
        try:
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath)))
            return element
        except NoSuchElementException:
            continue
    raise Exception("Element could not be located with any known XPaths.")

def fix_csv_delimiter(file_path):
    """Check and fix the delimiter in a CSV file."""
    with open(file_path, 'r', newline='', encoding='utf-8') as infile:
        first_line = infile.readline()

        # Check if the delimiter is a semicolon
        if ';' in first_line:
            print("Detected semicolon delimiter, fixing the file...")
            # Create a new file with commas as delimiters
            fixed_file_path = file_path.replace(".csv", "_fixed.csv")
            with open(fixed_file_path, 'w', newline='', encoding='utf-8') as outfile:
                # Replace all semicolons with commas
                for line in infile:
                    outfile.write(line.replace(';', ','))
            return fixed_file_path
        else:
            print("Delimiter is already correct (comma), no changes needed.")
            return file_path
    
    fixed_file_path = file_path.replace(".csv", "_fixed.csv")
    with open(file_path, 'r', newline='', encoding='utf-8') as infile, \
         open(fixed_file_path, 'w', newline='', encoding='utf-8') as outfile:
        reader = csv.reader(infile, delimiter=';')
        writer = csv.writer(outfile, delimiter=',', quoting=csv.QUOTE_ALL)
        for row in reader:
            writer.writerow(row)
    return fixed_file_path


from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
import time
import pickle

# Track usernames that have already received messages
sent_messages_log = set()

def locate_element_with_fallback(driver, xpaths, wait_time=10):
    """Try multiple XPATH selectors until one finds an element."""
    for xpath in xpaths:
        try:
            element = WebDriverWait(driver, wait_time).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            return element
        except:
            continue
    raise Exception("None of the provided XPATHs could locate an element.")

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
import time
import pickle

# Track usernames that have already received messages
sent_messages_log = set()

def locate_element_with_fallback(driver, xpaths, wait_time=10):
    """Try multiple XPATH selectors until one finds an element."""
    for xpath in xpaths:
        try:
            element = WebDriverWait(driver, wait_time).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            return element
        except:
            continue
    raise Exception("None of the provided XPATHs could locate an element.")

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
import time
import pickle

# Track usernames that have already received messages
sent_messages_log = set()

def locate_element_with_fallback(driver, xpaths, wait_time=10):
    """Try multiple XPATH selectors until one finds an element."""
    for xpath in xpaths:
        try:
            element = WebDriverWait(driver, wait_time).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            return element
        except:
            continue
    raise Exception("None of the provided XPATHs could locate an element.")

def send_dm(target_username, name, message_text, follow_after=False):
    """Send a DM to the specified username with enhanced error handling and debugging."""
    driver = None
    try:
        print(f"\n=== Starting DM process for {name} ({target_username}) ===")
        
        if target_username in sent_messages_log:
            print(f"Skipping {target_username} - message already sent.")
            return f"Skipped {target_username} - message already sent."

        driver = initialize_driver()
        print("Driver initialized successfully")
        
        driver.get("https://www.instagram.com")
        time.sleep(3)
        print("Loaded Instagram homepage")

        # Load cookies with error handling
        try:
            with open(SESSION_FILE, "rb") as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            driver.refresh()
            time.sleep(3)
            print("Session cookies loaded successfully")
        except FileNotFoundError:
            print("ERROR: Session file not found")
            return "Session not found. Please log in first."
        except Exception as e:
            print(f"ERROR loading cookies: {str(e)}")
            return f"Error loading session: {str(e)}"

        # Navigate to DM page with explicit wait
        driver.get("https://www.instagram.com/direct/new/")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(5)
        print("Loaded DM page")

        # Handle notifications popup with explicit try-except
        try:
            not_now_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[text()='Not Now' or text()='Not now' or contains(text(), 'Later')]"))
            )
            not_now_button.click()
            print("Dismissed notifications popup")
        except Exception as e:
            print(f"No notifications popup or couldn't dismiss: {str(e)}")

        # Click "Send message" with multiple attempts
        send_message_xpaths = [
            "//div[contains(@role, 'button') and contains(text(), 'Send message')]",
            "//button[contains(text(), 'Send message')]",
            "//div[contains(@class, 'x1ey2m1c')]//div[@role='button']"
        ]
        
        message_button_found = False
        for xpath in send_message_xpaths:
            try:
                send_message_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                send_message_button.click()
                message_button_found = True
                print("Clicked 'Send message' button successfully")
                break
            except Exception:
                continue
                
        if not message_button_found:
            raise Exception("Could not locate or click 'Send message' button")

        time.sleep(3)

        # Search for user with explicit wait
        try:
            recipient_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@name='queryBox' or @placeholder='Search...']"))
            )
            recipient_input.clear()
            recipient_input.send_keys(target_username)
            time.sleep(3)
            print(f"Entered username in search: {target_username}")
        except Exception as e:
            print(f"ERROR finding search input: {str(e)}")
            raise

        # Enhanced user selection with JavaScript click
        try:
            search_results = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'x9f619')]//span"))
            )
            
            found = False
            for result in search_results:
                user_name = result.text.strip()
                print(f"Found user in results: '{user_name}'")
                if user_name and name.strip().lower() in user_name.lower():
                    print(f"Matched user: {user_name}")
                    try:
                        driver.execute_script("arguments[0].scrollIntoView(true);", result)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", result)
                        found = True
                        print("Successfully clicked on user")
                        time.sleep(5)  # Wait for messages to load
                
                        # Try finding the bottom acceptance message
                        acceptance_text = "You can send more messages after your invite is accepted."
                        try:
                            elements = driver.find_elements(By.XPATH, "//div")
                            for element in elements:
                                if acceptance_text.lower() in element.text.lower():
                                    print(f"Found restriction message: {element.text}")
                                    return "Message in requests"
                        except Exception as e:
                            print(f"Error checking text: {str(e)}")
                            
                        # One more try with direct page source
                        try:
                            if acceptance_text.lower() in driver.page_source.lower():
                                print("Found restriction message in page source")
                                return "Message in requests"
                        except Exception as e:
                            print(f"Error checking page source: {str(e)}")
                            
                        print("No invite/restriction message found, proceeding with normal flow")
                        break
                    except Exception as e:
                        print(f"ERROR clicking user with JS: {str(e)}")
                        raise
            
            if not found:
                raise Exception(f"Could not find exact match for {name}")
            
            time.sleep(3)
        except Exception as e:
            print(f"ERROR during user selection: {str(e)}")
            raise

        # Now proceed with chat button only if we haven't returned due to restrictions
        chat_button_xpaths = [
            "//div[text()='Next']",
            "//div[text()='Chat']",
            "//button[contains(@class, '_acan')]"
        ]
        
        chat_button_clicked = False
        for xpath in chat_button_xpaths:
            try:
                chat_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                chat_button.click()
                chat_button_clicked = True
                print("Clicked chat/next button")
                break
            except Exception:
                continue
        
        if not chat_button_clicked:
            raise Exception("Could not locate or click chat/next button")

        time.sleep(5)

        # Send the message
        message_box_selectors = [
            "//div[contains(@role, 'textbox')]",
            "//p[contains(@class, 'xat24cr')]",
            "//textarea[contains(@placeholder, 'Message')]",
        ]
        
        message_sent = False
        for selector in message_box_selectors:
            try:
                message_box = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                
                # Wait for element to be interactive
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                
                # Try to send message
                message_box.click()
                time.sleep(1)
                message_box.send_keys(message_text)
                time.sleep(1)
                message_box.send_keys(Keys.RETURN)
                
                message_sent = True
                print(f"Message sent successfully using selector: {selector}")
                break
            except Exception as e:
                print(f"Failed with selector {selector}, trying next...")
                continue

        if not message_sent:
            # Final JavaScript attempt
            try:
                driver.execute_script("""
                    var messageBox = document.querySelector('div[role="textbox"]');
                    if (messageBox) {
                        messageBox.click();
                        messageBox.focus();
                        return true;
                    }
                    return false;
                """)
                time.sleep(1)
                webdriver.ActionChains(driver).send_keys(message_text).send_keys(Keys.RETURN).perform()
                message_sent = True
                print("Message sent successfully using JavaScript method")
            except Exception as e:
                raise Exception("Could not send message using any available method")

        # Verify message was sent
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, f"//div[contains(text(), '{message_text[:20]}')]"))
            )
            print("Message delivery confirmed")
            sent_messages_log.add(target_username)
        except Exception:
            print("Could not confirm message delivery")

        if follow_after:
            try:
                follow_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='Follow' or contains(@class, '_acan')]"))
                )
                follow_button.click()
                print("Followed user successfully")
                time.sleep(2)
            except Exception as e:
                print(f"WARNING: Could not follow user: {str(e)}")

        return "Message sent successfully"

    except Exception as e:
        error_msg = f"ERROR in send_dm: {str(e)}"
        print(error_msg)
        if driver:
            try:
                screenshot_path = f"error_screenshot_{target_username}_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                print(f"Error screenshot saved to {screenshot_path}")
            except Exception as screenshot_error:
                print(f"Could not save error screenshot: {str(screenshot_error)}")
        return error_msg

    finally:
        if driver:
            driver.quit()
            print("Driver closed successfully")

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    login_and_save_session(username, password)
    return redirect(url_for("home"))


# Add these routes to update the frontend
@app.route("/get_current_status")
def get_current_status():
    return jsonify(CURRENT_STATUS)

@app.route("/reset_status", methods=["POST"])
def reset_status():
    global CURRENT_STATUS
    CURRENT_STATUS = {"current": 0, "total": 0, "messages": []}
    return jsonify({"status": "reset"})

import csv
import os

def fix_csv_delimiter(file_path):
    """Check and fix the delimiter in a CSV file, preserving the header."""
    with open(file_path, 'r', newline='', encoding='utf-8') as infile:
        content = infile.readlines()

        if ';' in content[0]:  # Check if semicolon is used in the header
            print("Detected semicolon delimiter, fixing the file...")
            fixed_file_path = file_path.replace(".csv", "_fixed.csv")
            with open(fixed_file_path, 'w', newline='', encoding='utf-8') as outfile:
                header = content[0].replace(";", ",")
                outfile.write(header)

                for line in content[1:]:
                    outfile.write(line.replace(";", ","))
            return fixed_file_path
        else:
            print("Delimiter is already correct (comma), no changes needed.")
            return file_path


from flask import jsonify
import os
import csv
import time

LOG_FILE = "dm_log.csv"  # Define the log file name
PROGRESS_FILE = "progress.txt"  # Define the progress file

@app.route("/send_bulk_dms", methods=["POST"])
def send_bulk_dms():
    global CURRENT_STATUS
    
    # Reset status for new batch
    CURRENT_STATUS = {"current": 0, "total": 0, "messages": []}
    
    # Get the logged-in username from the session file
    session_username = None
    try:
        with open(SESSION_FILE, "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                if cookie.get('name') == 'ds_user_id':  # Instagram's username cookie
                    session_username = cookie.get('value')
                    break
    except:
        return jsonify({"error": "Not logged in"})

    # Get form data and file
    csv_file = request.files["csv_file"]
    message_delay = int(request.form["message_delay"])
    num_dms = int(request.form["num_dms"])

    # Process CSV and count total messages
    csv_file_path = os.path.join('uploads', csv_file.filename)
    csv_file.save(csv_file_path)
    fixed_csv_path = fix_csv_delimiter(csv_file_path)

    # Count total messages to be sent
    with open(fixed_csv_path, 'r', newline='', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        next(csv_reader)  # Skip header
        total_messages = sum(1 for row in csv_reader if len(row) == 3)
    
    CURRENT_STATUS["total"] = min(total_messages, num_dms)

    # Process messages
    with open(fixed_csv_path, "r", newline='', encoding='utf-8') as file:
        csv_reader = csv.reader(file, delimiter=",")
        next(csv_reader)  # Skip header

        for row in csv_reader:
            if len(row) != 3:
                continue

            username, name, message = row[:3]
            
            # Check if already messaged
            if check_if_messaged(session_username, username):
                status = "Already messaged"
            else:
                # Send DM
                status = send_dm(username, name, message)
                if status == "Message sent successfully":
                    save_to_history(session_username, username, status, message)

            # Update status for frontend
            CURRENT_STATUS["current"] += 1
            CURRENT_STATUS["messages"].append({
                "username": username,
                "status": status
            })

            # Stop if we've reached the limit
            if CURRENT_STATUS["current"] >= num_dms:
                break

            time.sleep(message_delay)

    os.remove(csv_file_path)
    return jsonify(CURRENT_STATUS)



PROGRESS_FILE = "progress.txt"  # Define the progress file

def read_progress():
    """Read the progress from the file, if it exists. Returns the index to start from."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as file:
            progress = file.read()
            if progress.isdigit():
                return int(progress)
    return 0  # If no progress file or empty, start from the beginning


def update_progress(index):
    """Update the progress in the progress file."""
    with open(PROGRESS_FILE, 'w') as file:
        file.write(str(index))


if __name__ == "__main__":
    app.run(debug=True)