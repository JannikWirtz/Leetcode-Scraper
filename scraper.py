import time
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
import time
import csv
import pickle
from datetime import datetime, timedelta

# Set the path for cookies file and ChromeDriver
COOKIES_LOCATION = "cookies.pkl"

def save_cookies(browser, location):
    with open(location, 'wb') as file:
        pickle.dump(browser.get_cookies(), file)

def load_cookies(browser, location, url=None):
    with open(location, 'rb') as cookies_file:
        cookies = pickle.load(cookies_file)
        browser.delete_all_cookies()
        url_before_cookies = url or browser.current_url
        browser.get(url_before_cookies)
        for cookie in cookies:
            if isinstance(cookie.get('expiry'), float):  # Convert expiry from float to int
                cookie['expiry'] = int(cookie['expiry'])
            browser.add_cookie(cookie)

def getDriver():
    options = Options()
    options.add_argument("--window-size=1200, 800")
    options.add_argument("--disable-notifications")
    options.add_argument("--lang=en-GB")
    input_driver = webdriver.Chrome()
    input_driver.get('https://leetcode.com/')

    return input_driver


def convert_time_ago_to_date(time_string, current_date):
    time_string = time_string.split('ago')[0].strip()
    segments = time_string.split(',')
    total_timedelta = timedelta()
    for segment in segments:
        segment = segment.strip()
        if 'week' in segment:
            weeks = int(segment.split()[0])
            total_timedelta += timedelta(weeks=weeks)
        elif 'day' in segment:
            days = int(segment.split()[0])
            total_timedelta += timedelta(days=days)
        elif 'hour' in segment:
            hours = int(segment.split()[0])
            total_timedelta += timedelta(hours=hours)
        elif 'minute' in segment:
            minutes = int(segment.split()[0])
            total_timedelta += timedelta(minutes=minutes)

    return current_date - total_timedelta



browser = getDriver()

try:
    # First, try to load previous session
    load_cookies(browser, COOKIES_LOCATION, "https://leetcode.com/")
    browser.get("https://leetcode.com/")

    # TODO: Add a condition to check if you are actually logged in. If not, raise an exception or error.

except (Exception, FileNotFoundError):
    # If load fails, you can manually login and then save cookies
    browser.get("https://leetcode.com/accounts/login/")
    # Manually login here
    input("Log in to LeetCode in the browser and then press Enter here...")
    save_cookies(browser, COOKIES_LOCATION)


# read all previous submissions
import pandas as pd
df = pd.read_csv('leetcode_submissions.csv', delimiter=';')

def extractSubmissions():
    all_rows_data = []
    page_number = 1
    while page_number < 20:
        # Get the next page of submissions
        submissions_url = f'https://leetcode.com/submissions/#/{page_number}'
        browser.get(submissions_url)
        time.sleep(5)  # Let the page load

        # Extract Data from Table
        try:
            rows = browser.find_elements_by_xpath("/html/body/div[2]/div/div/div/div/div/div/table/tbody/tr")
            
            if not rows:
                break  # End loop if no rows found
            
            current_date = datetime.now()

            for row in rows:
                time_submitted = row.find_element_by_xpath(".//td[1]").text
                actual_date = convert_time_ago_to_date(time_submitted, current_date)

                question = row.find_element_by_xpath(".//td[2]").text
                status_link_element = row.find_element_by_xpath(".//td[3]/a")
                status = status_link_element.text
                status_link = status_link_element.get_attribute("href")
                runtime = row.find_element_by_xpath(".//td[4]").text
                language = row.find_element_by_xpath(".//td[5]").text

                # Check if this question at the same date is already in the CSV
                if len(df[(df['Date'] == actual_date.strftime('%Y-%m-%d')) & (df['Question'] == question)]) > 0:
                    return all_rows_data

                all_rows_data.append([actual_date.strftime('%Y-%m-%d'), question, status, runtime, language, status_link])

            page_number += 1

        except NoSuchElementException:
            break  # End loop if no table is found

        return all_rows_data
    
all_rows_data = extractSubmissions()

# Save to CSV
# append previous csv data to all_rows_data
all_rows_data.extend(df.values.tolist())

with open('leetcode_submissions.csv', 'w', newline='') as file:
    writer = csv.writer(file, delimiter=';')
    writer.writerow(["Date", "Question", "Status", "Runtime", "Language", "Status Link"])
    writer.writerows(all_rows_data)

# Close the browser
browser.close()