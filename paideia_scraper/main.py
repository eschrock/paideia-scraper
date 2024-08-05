from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import os
import sys
import json
import time
from selenium.common.exceptions import NoSuchElementException


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


def get_current_group_id(driver):
    pagination_elem = driver.find_element(By.CLASS_NAME, "fsElementPagination")
    raw_params = pagination_elem.get_attribute("data-searchparams")
    search_params = json.loads(raw_params)
    return search_params["const_search_location"]


def get_class_students(driver, class_name):
    # Make sure "Location" is visible, as after login
    WebDriverWait(driver, 600).until(
        EC.presence_of_element_located((By.NAME, "const_search_location"))
    )

    # Set the location
    select_elem = driver.find_element(By.NAME, "const_search_location")
    select = Select(select_elem)
    select.select_by_visible_text(class_name)
    group_id = select.first_selected_option.get_attribute("value")
    print(f"Looking up students in class '{class_name}' ({group_id})")
    select_elem.submit()

    # Make sure the given clas is loaded
    current_group_id = get_current_group_id(driver)
    while current_group_id != group_id:
        time.sleep(1)
        current_group_id = get_current_group_id(driver)

    # Fetch all student elements
    students = {}
    student_elem_list = driver.find_elements(By.CLASS_NAME, "fsConstituentProfileLink")
    for student_elem in student_elem_list:
        try:
            # This class appears twice, ignore the second case with a child span
            student_elem.find_element(By.TAG_NAME, "span")
        except NoSuchElementException:
            student_name = student_elem.text.strip()
            print(f"Found student {student_name}")
            students[student_name] = student_elem

    return students


def get_parent_info(driver, students):
    pass


def main() -> int:
    if len(sys.argv) != 2:
        exit("usage: scrape <class name>")
    driver = login()
    students = get_class_students(driver, sys.argv[1])
    get_parent_info(driver, students)
    return 0


if __name__ == "__main__":
    sys.exit(main())  # next section explains the use of sys.exit
