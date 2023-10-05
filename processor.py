from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import csv
import pandas as pd
import pickle
import time

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

browser = getDriver()

try:
    # First, try to load previous session
    load_cookies(browser, COOKIES_LOCATION, "https://leetcode.com/")
    browser.get("https://leetcode.com/")
except (Exception, FileNotFoundError):
    # If load fails, you can manually login and then save cookies
    browser.get("https://leetcode.com/accounts/login/")
    # Manually login here
    input("Log in to LeetCode in the browser and then press Enter here...")
    save_cookies(browser, COOKIES_LOCATION)

previouslyProcessed = pd.read_csv('processed_leetcode_data.csv', delimiter=';')

# Read CSV and get unique problems
df = pd.read_csv('leetcode_submissions.csv', delimiter=';')
unique_questions = df['Question'].unique()
result_data = []

# For each unique problem
for question in unique_questions:
    submissions = df[df['Question'] == question]
    latest_submission = submissions.iloc[0]
    date = latest_submission['Date']
    # change date format to match previouslyProcessed %d-%m-%Y
    date = date.split(" ")[0]
    date = date.split("-")
    date = f"{date[2]}-{date[1]}-{date[0][2:]}"

    status_link = latest_submission['Status Link']

    # Navigate to the submission link
    browser.get(status_link)
    time.sleep(3)

    # Get problem link using your provided method
    try:
        problem_link_element = browser.find_element_by_xpath("//a[contains(@class, 'inline-wrap')]") # //*[@id="submission-app"]/div/div[1]/h4/a
        problem_link = problem_link_element.get_attribute('href')
    except Exception as e:
        print(f"Failed to extract problem link for question: {question}")
        continue
    
    # Go to the problem page to get difficulty, likes, and dislikes
    browser.get(problem_link)
    time.sleep(5)

    try:
        question_element = browser.find_element_by_xpath("//a[contains(@class, 'mr-2 text-label-1 dark:text-dark-label-1 hover:text-label-1 dark:hover:text-dark-label-1 text-lg font-medium')]")
        question_text = question_element.text.strip()  # This will give e.g., "198. House Robber"
        question_number = question_text.split(".")[0]  # This will give "198"
    except Exception as e:
        print(f"Failed to extract question number for question: {question}")
        question_number = "N/A"

    # Check if this question at the same date is already in the processed data
    if len(previouslyProcessed[(previouslyProcessed['Date'] == date) & (previouslyProcessed['Question Number'] == int(question_number))]) > 0:
        print(f"Ending Processing: question {question} already processed on date {date}.")
        break


    try:
        # click away dynamic layout if popup appears
        try:
            popup = browser.find_element_by_xpath("//*[@id='headlessui-portal-root']/div[1]/div/div/div/div[2]/div[1]/button")
            popup.click()
            time.sleep(1)
        except Exception as e:
            tags = [] # skip step... do nothing
            
        reveal_tags_element = browser.find_element_by_xpath("//*[contains(text(), 'Related Topics')]")
        reveal_tags_element.click()
        tries = 0
        while tries < 10:
            tries += 1
            try:
                tags_elements = browser.find_elements_by_xpath("//*[@class='overflow-hidden transition-all duration-500']")
                for tag in tags_elements:
                    if tag.text == '':
                        continue
                    tags = tag.text.split("\n")
                if tags == [''] or tags == []:
                    time.sleep(1)
                else:
                    break
            except Exception as e:
                time.sleep(.5)
    except Exception as e:
        print(f"Failed to extract tags for question: {question}")
        tags = []

    try:
        difficulty_element = browser.find_element_by_xpath("//*[@id='qd-content']/div[1]/div/div/div/div[2]/div/div/div[1]/div/div[2]/div[1]")
        difficulty = difficulty_element.text.strip()
    except Exception as e:
        print(f"Failed to extract difficulty for question: {question}")
        continue

    # Get likes using your provided XPath
    likes_element = browser.find_element_by_xpath("//*[@id='qd-content']/div[1]/div/div/div/div[2]/div/div/div[1]/div/div[2]/div[3]/div[1]/div[2]")
    likes_text = likes_element.text
    # Convert likes text (like "5.7K") to an integer
    if 'K' in likes_text:
        likes = int(float(likes_text.replace('K', '')) * 1000)
    else:
        likes = int(likes_text.replace(',', ''))

    dislikes_element = browser.find_element_by_xpath("//*[@id='qd-content']/div[1]/div/div/div/div[2]/div/div/div[1]/div/div[2]/div[3]/div[2]/div[2]")
    dislikes_text = dislikes_element.text
    # Convert likes text (like "5.7K") to an integer
    if 'K' in dislikes_text:
        dislikes = int(float(dislikes_text.replace('K', '')) * 1000)
    else:
        dislikes = int(dislikes_text.replace(',', ''))

    # Extract acceptance rate
    try:
        acceptance_rate_element = browser.find_element_by_xpath("//*[@id='qd-content']/div[1]/div/div/div/div[2]/div/div/div[4]/div/div[5]/div[2]/span")
        acceptance_rate = acceptance_rate_element.text.strip()
    except Exception as e:
        acceptance_rate = "N/A"

    num_accepted_submissions = len(submissions[submissions['Status'] == "Accepted"])
    # Count the not accepted submissions
    failed_submissions = len(submissions) - num_accepted_submissions
    # Adjust the tries according to whether there was a successful submission
    if num_accepted_submissions == 0:
        failed_submissions = -failed_submissions

    # remove time from date
    date = date.split(" ")[0]
    tags = "|".join(tags)

    ratio = str(int(round(dislikes / (likes + dislikes), 2) * 100)) + '%'
    
    # Append to result data
    result_data.append([date, question_number, problem_link, difficulty, likes, dislikes, ratio, acceptance_rate, failed_submissions, tags])
    print(result_data[-1])


# add all previous processed data to result_data
# result_data.extend(previouslyProcessed.values.tolist())
# append previouslyProcessed to result_data
result_data = pd.concat([previouslyProcessed, pd.DataFrame(result_data, columns=["Date","Question Number", "Link", "Difficulty", "Likes", "Dislikes", "Dislike ratio", "Acceptance Rate", "Failed Submissions", "Tags"])])
df = pd.read_csv('leetcode_submissions.csv', delimiter=';')
final_result_data = []

# for every date, go through unique problems on that day and build result data based on data from that day only, ie. the number of tries, success rate
# result_data.append([date, question_number, problem_link, difficulty, likes, dislikes, ratio, acceptance_rate, failed_submissions, tags])

for date in df['Date'].unique():
    # get all submissions on this date
    date_submissions = df[df['Date'] == date]
    # date to d-m-y
    date = date.split(" ")[0]
    date = date.split("-")
    date = f"{date[2]}-{date[1]}-{date[0][2:]}"
    # get all unique questions on this date
    unique_question_links = result_data[result_data['Date'] == date]['Link'].unique()
    
    # for each unique question, get the number of submissions, number of accepted submissions, and number of failed submissions
    for question_link in unique_question_links:
        # problem: df contains only question title ie. Product of Array Except Self
        # result_data contains question number ie. 238 and 
        # get question name from number
        # extract question title from link https://leetcode.com/problems/product-of-array-except-self/
        question_name = question_link.split("/")[-2]
        question_name = question_name.replace('-', ' ') # is in lowercase
        # compare lowercase of  date_submissions['Question'] with lowercase of question_name
        submissions = date_submissions[date_submissions['Question'].str.lower() == question_name.lower()] 
        # disregads submissions with Status == "Runtime Error" or "Time Limit Exceeded" or "Memory Limit Exceeded" or "Compile Error"
        submissions = submissions[~submissions['Status'].isin(["Runtime Error", "Time Limit Exceeded", "Memory Limit Exceeded", "Compile Error"])]

        num_accepted_submissions = len(submissions[submissions['Status'] == "Accepted"])
        # Count the not accepted submissions
        failed_submissions = len(submissions) - num_accepted_submissions
        # Adjust the tries according to whether there was a successful submission
        if num_accepted_submissions == 0:
            failed_submissions = -failed_submissions

        # remove time from date
        date = date.split(" ")[0]
        # get tags of problem from result_data
        difficulty = result_data[result_data['Link'] == question_link]['Difficulty'].values[0]
        likes = result_data[result_data['Link'] == question_link]['Likes'].values[0]
        dislikes = result_data[result_data['Link'] == question_link]['Dislikes'].values[0]
        ratio = result_data[result_data['Link'] == question_link]['Dislike ratio'].values[0]
        acceptance_rate = result_data[result_data['Link'] == question_link]['Acceptance Rate'].values[0]
        tags = result_data[result_data['Link'] == question_link]['Tags'].values[0]
        question_num = result_data[result_data['Link'] == question_link]['Question Number'].values[0]
        
        # Append to result data
        final_result_data.append([date, question_num, question_link, difficulty, likes, dislikes, ratio, acceptance_rate, failed_submissions, tags])
        print(final_result_data[-1])




# Save to a new CSV
result_file = 'processed_leetcode_data.csv'
with open(result_file, 'w', newline='') as file:
    writer = csv.writer(file, delimiter=';')
    writer.writerow(["Date","Question Number", "Link", "Difficulty", "Likes", "Dislikes", "Dislike ratio", "Acceptance Rate", "Failed Submissions", "Tags"])
    writer.writerows(final_result_data)

print(f"Processed data saved to {result_file}")

# Close the browser
browser.close()
