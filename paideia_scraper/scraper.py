import logging
import json
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import NoSuchElementException

from .mock import MOCK_STUDENTS


class Scraper:
    # Static configuration
    TIMEOUT = 60

    def __init__(self, config):
        """Initialize the scraper with a new Chrome webdriver instance and config."""
        # Use Selenium Manager to automatically handle ChromeDriver
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        self._driver = webdriver.Chrome(options=options)
        self._logger = logging.getLogger(__name__)
        self._config = config

    @property
    def driver(self):
        """Get the webdriver instance for direct access during migration."""
        return self._driver

    def login(self):
        """Log into the Paideia School parent portal."""
        self._logger.info(f"Logging into {self._config.paideia_portal_url}...")
        self._driver.get(self._config.paideia_portal_url)

        # Enter username and password
        user_elem = self._driver.find_element(By.NAME, "username")
        user_elem.send_keys(self._config.paideia_user)

        password_elem = self._driver.find_element(By.NAME, "password")
        password_elem.send_keys(self._config.paideia_password)
        password_elem.submit()

        # Wait for Student Directory link to appear
        self._logger.debug("Waiting for Student Directory link...")
        student_dir_link = WebDriverWait(self._driver, self.TIMEOUT).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//a[contains(@href, '/pythons/parent-portal/student-directory')]",
                )
            )
        )

        # Get the URL and navigate to it
        student_dir_url = student_dir_link.get_attribute("href")
        self._logger.info(f"Navigating to Student Directory: {student_dir_url}")
        self._driver.get(student_dir_url)

        # Wait for the search location field to appear
        self._logger.debug("Waiting for search location field...")
        WebDriverWait(self._driver, self.TIMEOUT).until(
            EC.presence_of_element_located((By.NAME, "const_search_location"))
        )

    def _get_current_group_id(self):
        """Get the current group ID from the pagination element."""
        pagination_elem = self._driver.find_element(
            By.CLASS_NAME, "fsElementPagination"
        )
        raw_params = pagination_elem.get_attribute("data-searchparams")
        search_params = json.loads(raw_params)
        return search_params["const_search_location"]

    def _select_class(self, class_name):
        """
        Select a class from the dropdown and wait for the page to update.

        Args:
            class_name: Name of the class to select

        Raises:
            ValueError: If the class name is not found in the dropdown
            TimeoutError: If the page doesn't update within the timeout period
        """
        # Find and select the class
        select_elem = self._driver.find_element(By.NAME, "const_search_location")
        select = Select(select_elem)

        # Check if the class exists in the dropdown
        try:
            select.select_by_visible_text(class_name)
        except Exception as e:
            available_options = [option.text for option in select.options]
            raise ValueError(
                f"Class '{class_name}' not found. Available options: {available_options}"
            ) from e

        # Get the group ID for the selected class
        group_id = select.first_selected_option.get_attribute("value")
        self._logger.info(f"Selected class '{class_name}' with group ID: {group_id}")

        # Submit the form
        select_elem.submit()

        # Wait for the page to update with the new class data
        try:
            WebDriverWait(self._driver, self.TIMEOUT).until(
                lambda driver: self._get_current_group_id() == group_id
            )
            self._logger.debug(f"Class '{class_name}' data loaded successfully")
        except Exception as e:
            raise TimeoutError(
                f"Timeout waiting for class '{class_name}' data to load"
            ) from e

    def _fetch_students_from_page(self, mock_parents=False):
        """
        Fetch student information from the current page.

        Args:
            mock_parents: If True, generate mock parent data.
                          If False, extract real parent names.

        Returns:
            List of student dictionaries with name, class, and parents
        """
        self._logger.debug(
            f"Starting _fetch_students_from_page, mock_parents={mock_parents}"
        )
        students = []

        # Find all student item containers
        self._logger.debug("Looking for student item containers...")
        student_items = self._driver.find_elements(By.CLASS_NAME, "fsConstituentItem")
        self._logger.debug(f"Found {len(student_items)} student items")

        for item_idx, item in enumerate(student_items):
            self._logger.debug(
                f"Processing student item {item_idx + 1}/{len(student_items)}"
            )
            try:
                # Wait for student name to be populated
                self._logger.debug(
                    f"Waiting for name element in item {item_idx + 1}..."
                )
                name_elem = WebDriverWait(item, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "fsFullName"))
                )

                # Wait for the name text to be non-empty
                self._logger.debug(
                    f"Waiting for name text to be populated in item {item_idx + 1}..."
                )
                WebDriverWait(item, 10).until(lambda x: name_elem.text.strip() != "")

                student_name = name_elem.text.strip()
                self._logger.debug(
                    f"Extracted name: '{student_name}' from item {item_idx + 1}"
                )

                # Skip students with empty names (shouldn't happen now, but safety check)
                if not student_name:
                    continue

                # Wait for location to be populated
                self._logger.debug(
                    f"Waiting for location element in item {item_idx + 1}..."
                )
                location_elem = WebDriverWait(item, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "fsLocations"))
                )

                # Wait for the location text to be non-empty
                self._logger.debug(
                    f"Waiting for location text to be populated in item {item_idx + 1}..."
                )
                WebDriverWait(item, 10).until(
                    lambda x: location_elem.text.strip() != ""
                )

                location_text = location_elem.text.strip()
                self._logger.debug(
                    f"Location text: '{location_text}' from item {item_idx + 1}"
                )

                # Take only the part before the first comma
                class_name = location_text.split(",")[0].strip()
                self._logger.debug(
                    f"Extracted class: '{class_name}' from item {item_idx + 1}"
                )

                # Get parent information
                self._logger.debug(
                    f"Getting parent info for item {item_idx + 1}, mock_parents={mock_parents}"
                )
                if mock_parents:
                    # Generate mock parent data
                    self._logger.debug(
                        f"Generating mock parents for item {item_idx + 1}"
                    )
                    num_parents = random.randint(1, 2)
                    from .mock import mock_parents as mock_parents_func

                    parents = mock_parents_func(num_parents)
                    self._logger.debug(
                        f"Generated {len(parents)} mock parents for item {item_idx + 1}"
                    )
                else:
                    # Extract real parent names and store student element for later parent info extraction
                    self._logger.debug(
                        f"Extracting real parent names for item {item_idx + 1}"
                    )

                    # Find the clickable profile link within this item
                    profile_link = item.find_element(
                        By.CLASS_NAME, "fsConstituentProfileLink"
                    )
                    self._logger.debug(f"Found profile link for item {item_idx + 1}")

                    parent_names = self._get_student_parents(profile_link)
                    self._logger.debug(
                        f"Found {len(parent_names)} real parent names: {parent_names}"
                    )

                    parents = []
                    for parent_name in parent_names:
                        parent = {
                            "name": parent_name,
                            "email": None,  # Will be filled in second pass
                            "phone": None,  # Will be filled in second pass
                        }
                        parents.append(parent)

                    # If no parents found, create a placeholder
                    if not parents:
                        self._logger.debug(
                            f"No real parents found for item {item_idx + 1}, creating placeholder"
                        )
                        from .mock import mock_parents as mock_parents_func

                        parents = mock_parents_func(1)
                        self._logger.debug(
                            f"Created {len(parents)} placeholder parents for item {item_idx + 1}"
                        )

                    # Store the student element for later parent info extraction
                    student_element = profile_link

                student = {
                    "name": student_name,
                    "class": class_name,
                    "parents": parents,
                    "student_element": student_element,  # Store for later parent info extraction
                }

                students.append(student)
                self._logger.debug(
                    f"Found student: {student_name} in class: {class_name} with {len(parents)} parents"
                )

            except Exception as e:
                self._logger.warning(f"Could not extract student info from item: {e}")
                continue

        self._logger.info(f"Extracted {len(students)} students from page")
        return students

    def _extract_parent_contact_info_for_page(self, students):
        """
        Extract contact information for all parents on the current page.
        This should be called after all students have been processed but before moving to the next page.

        Args:
            students: List of student dictionaries with student_element and parents
        """
        self._logger.info(
            f"Extracting parent contact info for {len(students)} students on this page"
        )

        for student_idx, student in enumerate(students):
            try:
                self._logger.debug(
                    f"Processing parent contact info for student {student_idx + 1}: {student['name']}"
                )

                # Get the stored student element
                student_element = student.get("student_element")
                if not student_element:
                    self._logger.warning(
                        f"No student element stored for {student['name']}, skipping"
                    )
                    continue

                    # Process each parent
                for parent_idx, parent in enumerate(student["parents"]):
                    try:
                        self._logger.debug(
                            f"Processing parent {parent_idx + 1}: {parent['name']}"
                        )

                        # Open the student dialog for each parent (since parent dialog closes student dialog)
                        self._open_student_dialog(student_element)

                        # Open the parent dialog
                        contacts_elem = self._open_parent_dialog(
                            student_element, parent["name"]
                        )

                        # Extract contact information
                        contact_info = self._extract_parent_contact_info(contacts_elem)

                        # Update the parent with real contact info
                        parent["email"] = contact_info["email"]
                        parent["phone"] = contact_info["phone"]

                        self._logger.debug(
                            f"Updated parent {parent['name']} with contact info"
                        )

                        # Close the parent dialog (this also closes the student dialog)
                        self._close_parent_dialog()

                    except Exception as e:
                        self._logger.error(
                            f"Error processing parent {parent['name']} for student {student['name']}: {e}"
                        )
                        # Continue with other parents
                        continue

            except Exception as e:
                self._logger.error(
                    f"Error processing student {student['name']} for parent contact info: {e}"
                )
                # Continue with other students
                continue

        self._logger.info("Finished extracting parent contact info for this page")

    def _next_student_page(self):
        """
        Navigate to the next page of students if available.

        Returns:
            bool: True if successfully navigated to next page, False if no next page
        """
        try:
            # Look for the next page link
            next_page_link = self._driver.find_element(By.CLASS_NAME, "fsNextPageLink")

            # Click the next page link
            next_page_link.click()
            self._logger.debug("Navigating to next page")

            # Wait for the search location field to be present (indicates page loaded)
            WebDriverWait(self._driver, self.TIMEOUT).until(
                EC.presence_of_element_located((By.NAME, "const_search_location"))
            )

            self._logger.debug("Next page loaded successfully")
            return True

        except NoSuchElementException:
            # No next page link found
            return False
        except Exception as e:
            self._logger.error(f"Error navigating to next page: {e}")
            return False

    def _open_student_dialog(self, student_elem):
        """
        Open the student dialog by clicking on the student element.

        Args:
            student_elem: The student element to click on
        """
        from selenium.webdriver.common.action_chains import ActionChains

        action = ActionChains(self._driver)
        action.move_to_element(student_elem).click().perform()

        WebDriverWait(self._driver, self.TIMEOUT).until(
            EC.presence_of_element_located((By.CLASS_NAME, "fsRelationships"))
        )
        self._logger.debug("Student dialog opened successfully")

    def _close_student_dialog(self):
        """Close the student dialog."""
        self._logger.debug("Closing student dialog...")
        close_button = self._driver.find_element(By.CLASS_NAME, "fsDialogCloseButton")
        close_button.click()
        WebDriverWait(self._driver, self.TIMEOUT).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "fsRelationships"))
        )
        self._logger.debug("Student dialog closed successfully")

    def _open_parent_dialog(self, student_elem, parent_name):
        """
        Open the parent dialog by clicking on a specific parent within an open student dialog.

        Args:
            student_elem: The student element (should already have dialog open)
            parent_name: Name of the parent to open dialog for

        Returns:
            The contacts element for the parent
        """
        # Find parent elements within the open student dialog
        parent_elem_list = self._driver.find_elements(
            By.CLASS_NAME, "fsRelationshipParent"
        )

        for parent_elem in parent_elem_list:
            parent_link = parent_elem.find_element(
                By.CLASS_NAME, "fsConstituentProfileLink"
            )
            parent_elem_name = parent_link.text.strip()

            if parent_elem_name == parent_name:
                self._logger.debug(
                    f"Found parent {parent_name}, clicking to open dialog"
                )
                parent_link.click()

                # Wait for the contacts section to appear
                WebDriverWait(self._driver, self.TIMEOUT).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "fsContacts"))
                )

                contacts_elem = self._driver.find_element(By.CLASS_NAME, "fsContacts")
                self._logger.debug(f"Parent dialog opened for {parent_name}")
                return contacts_elem

        # If we get here, parent wasn't found
        raise ValueError(f"Failed to find parent {parent_name}")

    def _close_parent_dialog(self):
        """Close the parent dialog."""
        self._logger.debug("Closing parent dialog...")
        close_button = self._driver.find_element(By.CLASS_NAME, "fsDialogCloseButton")
        close_button.click()
        WebDriverWait(self._driver, self.TIMEOUT).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "fsContacts"))
        )
        self._logger.debug("Parent dialog closed successfully")

    def _extract_parent_contact_info(self, contacts_elem):
        """
        Extract email and phone information from a parent's contacts element.

        Args:
            contacts_elem: The contacts element for the parent

        Returns:
            Dictionary with email and phone (None if not found)
        """
        parent_info = {"email": None, "phone": None}

        try:
            # Get the contact email
            email_elem = contacts_elem.find_element(
                By.CSS_SELECTOR, ".fsEmailHome .fsStyleSROnly"
            )
            email = email_elem.text.strip()
            parent_info["email"] = email
            self._logger.debug(f"Found email: {email}")
        except NoSuchElementException:
            self._logger.debug("No email found for parent")

        # Get the contact mobile number
        try:
            mobile_elems = contacts_elem.find_elements(
                By.CSS_SELECTOR, ".fsPhoneMobile div"
            )
            if len(mobile_elems) > 1:
                phone_number = mobile_elems[1].text.strip()
                parent_info["phone"] = phone_number
                self._logger.debug(f"Found mobile number: {phone_number}")
            else:
                self._logger.debug("No mobile number found for parent")
        except NoSuchElementException:
            self._logger.debug("No mobile number found for parent")

        return parent_info

    def _get_student_parents(self, student_elem):
        """
        Get parent names for a student by opening their dialog.

        Args:
            student_elem: The student element to get parents for

        Returns:
            List of parent names
        """
        parent_names = []

        try:
            # Open the student dialog
            self._open_student_dialog(student_elem)

            # Find parents
            self._logger.debug("Looking for parent elements...")
            parent_elem_list = self._driver.find_elements(
                By.CLASS_NAME, "fsRelationshipParent"
            )

            for parent_elem in parent_elem_list:
                parent_link = parent_elem.find_element(
                    By.CLASS_NAME, "fsConstituentProfileLink"
                )
                parent_name = parent_link.text.strip()
                if parent_name:
                    parent_names.append(parent_name)
                    self._logger.debug(f"Found parent: {parent_name}")

        finally:
            # Always close the dialog
            self._logger.debug("Closing student dialog...")
            self._close_student_dialog()

        return parent_names

    def _get_class_student_info(self, class_name):
        """
        Get student information for a single class by scraping all pages.

        Args:
            class_name: Name of the class to scrape

        Returns:
            List of student dictionaries with name, class, and mock parents
        """
        self._logger.info(f"Processing class: {class_name}")

        # Select the class and wait for it to load
        self._select_class(class_name)

        class_students = []
        page_num = 1

        while True:
            self._logger.info(f"Fetching students from page {page_num}")

            # Fetch students from current page with parent info
            students_from_page = self._fetch_students_from_page(mock_parents=False)

            # Extract parent contact information for this page before moving to the next
            self._extract_parent_contact_info_for_page(students_from_page)

            class_students.extend(students_from_page)

            # Try to go to next page
            if not self._next_student_page():
                self._logger.debug(f"No more pages for class {class_name}")
                break

            page_num += 1

        # Clean up student objects by removing the stored elements
        for student in class_students:
            if "student_element" in student:
                del student["student_element"]

        self._logger.info(
            f"Total students collected for {class_name}: {len(class_students)}"
        )
        return class_students

    def _get_class_student_info_with_mock_parents(self, class_name):
        """
        Get student information for a single class by scraping all pages, using mock parents.

        Args:
            class_name: Name of the class to scrape

        Returns:
            List of student dictionaries with name, class, and mock parents
        """
        self._logger.info(f"Processing class: {class_name} with mock parents")

        # Select the class and wait for it to load
        self._select_class(class_name)

        class_students = []
        page_num = 1

        while True:
            self._logger.info(f"Fetching students from page {page_num}")

            # Fetch students from current page with mock parents
            students_from_page = self._fetch_students_from_page(mock_parents=True)
            class_students.extend(students_from_page)

            # Try to go to next page
            if not self._next_student_page():
                self._logger.debug(f"No more pages for class {class_name}")
                break

            page_num += 1

        self._logger.info(
            f"Total students collected for {class_name}: {len(class_students)}"
        )
        return class_students

    def get_student_info(self, mock=None, classes=None):
        """
        Get student information either from mock data or by scraping.

        Args:
            mock: Mock data type to use (e.g., "students") or None for real scraping
            classes: List of class names to scrape when not using mock data

        Returns:
            List of student dictionaries with name, class, and parents
        """
        if mock == "students":
            self._logger.info("Using mock student data")
            return MOCK_STUDENTS

        if classes:
            if mock == "parents":
                self._logger.info(
                    f"Scraping real student data with mock parents for classes: {classes}"
                )
            else:
                self._logger.info(f"Scraping real data for classes: {classes}")

            all_students = []

            for class_name in classes:
                try:
                    # Get student info for this class (always loops through pages)
                    if mock == "parents":
                        # Use mock parents
                        class_students = self._get_class_student_info_with_mock_parents(
                            class_name
                        )
                    else:
                        # Use real parent names
                        class_students = self._get_class_student_info(class_name)
                    all_students.extend(class_students)

                except Exception as e:
                    self._logger.error(f"Error processing class '{class_name}': {e}")
                    # Continue with other classes even if one fails
                    continue

            self._logger.info(f"Total students collected: {len(all_students)}")
            return all_students

        self._logger.warning("No mock data or classes specified")
        return []

    def close(self):
        """Close the webdriver and clean up resources."""
        if self._driver:
            self._driver.quit()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - automatically close the driver."""
        self.close()
