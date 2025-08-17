import argparse
import csv
import json
import logging
import os
import sys
import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from .config import load_config
from .scraper import Scraper
from .output import Output


def setup_logging(debug: bool = False):
    """Set up logging for all paideia_scraper classes."""
    level = logging.DEBUG if debug else logging.INFO

    # Configure root logger for paideia_scraper package
    logger = logging.getLogger("paideia_scraper")
    logger.setLevel(level)

    # Create console handler if none exists
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def main() -> int:
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Scrape student and parent information from Paideia School parent portal"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--login-only", action="store_true", help="Only perform login, then exit"
    )
    parser.add_argument(
        "--mock",
        metavar="TYPE",
        choices=["students"],
        help="Use mock data of specified type (can be combined with class names)",
    )
    parser.add_argument(
        "classes", nargs="*", help="Class names to scrape (can be combined with --mock)"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.login_only and not args.mock and not args.classes:
        parser.error(
            "Either --login-only, --mock, or at least one class name must be specified"
        )

    # Set up logging
    log = setup_logging(args.debug)

    config = load_config()
    scraper = Scraper(config)
    try:
        scraper.login()

        if args.login_only:
            log.info("Successfully logged in")
            return 0

        # Get student information
        students = scraper.get_student_info(mock=args.mock, classes=args.classes)

        if not students:
            log.info("No student data retrieved")
            return 1

        # Write to Excel file
        log.info("Writing to Excel file")

        # Ensure output directory exists
        os.makedirs("output", exist_ok=True)

        # Write to Excel file
        output = Output()
        excel_path = "output/class_list.xlsx"
        output.write_excel(students, excel_path)

        log.info(f"Data written to {excel_path}")
        return 0

    finally:
        scraper.close()


# Supporting functions - kept for future migration to scraper
def get_current_group_id(driver):
    pagination_elem = driver.find_element(By.CLASS_NAME, "fsElementPagination")
    raw_params = pagination_elem.get_attribute("data-searchparams")
    search_params = json.loads(raw_params)
    return search_params["const_search_location"]


def get_class_students(driver, class_name):
    # Set the location
    select_elem = driver.find_element(By.NAME, "const_search_location")
    select = Select(select_elem)
    select.select_by_visible_text(class_name)
    group_id = select.first_selected_option.get_attribute("value")
    # TODO: Replace with logging when migrated to scraper
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
            # TODO: Replace with logging when migrated to scraper
            print(f"Found student {student_name}")
            students[student_name] = student_elem

    return students


def open_student_dialog(driver, student_elem):
    action = ActionChains(driver)

    action.move_to_element(student_elem).click().perform()

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
            # TODO: Replace with logging when migrated to scraper
            print(f"Found parent {parent_name} for student {student_name}")

            student_parents[student_name][parent_name] = parent_elem

        close_student_dialog(driver)

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
            # TODO: Replace with logging when migrated to scraper
            print(f"Getting parent info for student {student_name}")
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
                # TODO: Replace with logging when migrated to scraper
                print(f"Found email {parent_name}: {email}")
            except NoSuchElementException:
                parent_info["email"] = None

            # Get the contact mobile number
            try:
                mobile_elems = contacts_elem.find_elements(
                    By.CSS_SELECTOR, ".fsPhoneMobile div"
                )
                if len(mobile_elems) > 0:
                    phone_number = mobile_elems[1].text.strip()
                    parent_info["phone"] = phone_number
                    # TODO: Replace with logging when migrated to scraper
                    print(f"Found mobile number {parent_name}: {phone_number}")
                else:
                    parent_info["phone"] = None
            except NoSuchElementException:
                parent_info["phone"] = None

            close_parent_dialog(driver)

            student_parent_info[student_name][parent_name] = parent_info

    return student_parent_info


def create_csv_dataset(parent_data):
    csv_data = [["Student", "Class", "Parent", "Email", "Phone"]]
    for class_name, students in parent_data.items():
        for student_name, parents in students.items():
            for parent_name, parent_info in parents.items():
                csv_data.append(
                    [
                        student_name,
                        class_name,
                        parent_name,
                        parent_info["email"],
                        parent_info["phone"],
                    ]
                )
    return csv_data


if __name__ == "__main__":
    sys.exit(main())
