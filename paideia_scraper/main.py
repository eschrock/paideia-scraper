from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import sys

STUDENT_DIRECTORY_URL = "https://www.paideiaschool.org/parent-portal/student-directory"


def login():
    user = os.environ.get("PAIDEIA_USER")
    if not user:
        exit("must set PAIDEIA_USER")
    password = os.environ.get("PAIDEIA_PASSWORD")
    if not password:
        exit("must set PAIDEIA_PASSWORD")

    driver = webdriver.Chrome()
    driver.get(STUDENT_DIRECTORY_URL)

    # Enter username and password
    user_elem = driver.find_element(By.NAME, "username")
    user_elem.send_keys(user)

    password_elem = driver.find_element(By.NAME, "password")
    password_elem.send_keys(password)
    password_elem.submit()

    return driver


def get_class_students(driver, class_name):
    # Wait until "Location" is visible
    WebDriverWait(driver, 600).until(
        EC.presence_of_element_located((By.NAME, "const_search_location"))
    )

    # Set the location


def main() -> int:
    if len(sys.argv) != 2:
        exit("usage: scrape <class name>")
    driver = login()
    get_class_students(driver, sys.argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())  # next section explains the use of sys.exit
