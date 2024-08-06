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
from pprint import pp


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


def open_student_dialog(driver, student_elem):
    student_elem.click()

    WebDriverWait(driver, 600).until(
        EC.presence_of_element_located((By.CLASS_NAME, "fsRelationships"))
    )


def close_student_dialog(driver):
    close_button = driver.find_element(By.CLASS_NAME, "fsDialogCloseButton")
    close_button.click()
    WebDriverWait(driver, 600).until(
        EC.invisibility_of_element_located((By.CLASS_NAME, "fsRelationships"))
    )


def get_student_parents(driver, students):
    student_parents = {}

    for student_name, student_elem in students.items():
        open_student_dialog(driver, student_elem)
        student_parents[student_name] = {}

        # Find parents
        parent_elem_list = driver.find_elements(By.CLASS_NAME, "fsRelationshipParent")
        for parent_elem in parent_elem_list:
            parent_link = parent_elem.find_element(
                By.CLASS_NAME, "fsConstituentProfileLink"
            )
            parent_name = parent_link.text.strip()
            print(f"Found parent {parent_name} for student {student_name}")

            student_parents[student_name][parent_name] = parent_elem

        close_student_dialog(driver)

        # Debug - return for now
        return student_parents

    return student_parents


def open_parent_dialog(driver, student_elem, parent_name):
    open_student_dialog(driver, student_elem)

    parent_elem_list = driver.find_elements(By.CLASS_NAME, "fsRelationshipParent")
    for parent_elem in parent_elem_list:
        parent_link = parent_elem.find_element(
            By.CLASS_NAME, "fsConstituentProfileLink"
        )
        parent_elem_name = parent_link.text.strip()

        if parent_elem_name == parent_name:
            parent_link.click()

            WebDriverWait(driver, 600).until(
                EC.presence_of_element_located((By.CLASS_NAME, "fsContacts"))
            )
            contacts_elem = driver.find_element(By.CLASS_NAME, "fsContacts")
            return contacts_elem

    exit(f"failed to find parent {parent_name}")


def close_parent_dialog(driver):
    close_button = driver.find_element(By.CLASS_NAME, "fsDialogCloseButton")
    close_button.click()
    WebDriverWait(driver, 600).until(
        EC.invisibility_of_element_located((By.CLASS_NAME, "fsContacts"))
    )


def get_parent_info(driver, students, parents):
    student_parent_info = {}

    for student_name, parents in parents.items():
        student_parent_info[student_name] = {}
        for parent_name in parents.keys():
            parent_info = {}
            contacts_elem = open_parent_dialog(
                driver, students[student_name], parent_name
            )

            # Get the contact email
            try:
                email_elem = contacts_elem.find_element(
                    By.CSS_SELECTOR, ".fsEmailHome .fsStyleSROnly"
                )
                email = email_elem.text.strip()
                parent_info["email"] = email
                print(f"Found email {parent_name}: {email}")
            except NoSuchElementException:
                parent_info["email"] = None

            # Get the contact mobile number
            try:
                mobile_elems = contacts_elem.find_elements(
                    By.CSS_SELECTOR, ".fsPhoneMobile div"
                )
                phone_number = mobile_elems[1].text.strip()
                parent_info["phone"] = phone_number
                print(f"Found mobile number {parent_name}: {phone_number}")
            except NoSuchElementException:
                parent_info["phone"] = None

            close_parent_dialog(driver)

            student_parent_info[student_name][parent_name] = parent_info

    return student_parent_info


def main() -> int:
    if len(sys.argv) != 2:
        exit("usage: scrape <class ...>")
    driver = login()
    students = get_class_students(driver, sys.argv[1])
    parents = get_student_parents(driver, students)
    parent_info = get_parent_info(driver, students, parents)
    pp(parent_info)
    return 0


if __name__ == "__main__":
    sys.exit(main())  # next section explains the use of sys.exit
