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

    def _extract_student_basic_info(self, item, item_idx):
        """
        Extract basic student information (name and class) from a student item element.

        Args:
            item: The student item DOM element
            item_idx: The index of the item (for logging purposes)

        Returns:
            tuple: (student_name, class_name) or (None, None) if extraction fails
        """
        try:
            # Wait for student name to be populated
            self._logger.debug(f"Waiting for name element in item {item_idx + 1}...")
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

            # Skip students with empty names
            if not student_name:
                self._logger.debug(
                    f"Empty student name for item {item_idx + 1}, skipping"
                )
                return None, None

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
            WebDriverWait(item, 10).until(lambda x: location_elem.text.strip() != "")

            location_text = location_elem.text.strip()
            self._logger.debug(
                f"Location text: '{location_text}' from item {item_idx + 1}"
            )

            # Take only the part before the first comma
            class_name = location_text.split(",")[0].strip()
            self._logger.debug(
                f"Extracted class: '{class_name}' from item {item_idx + 1}"
            )

            return student_name, class_name

        except Exception as e:
            self._logger.warning(
                f"Could not extract basic info for item {item_idx + 1}: {e}"
            )
            return None, None

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

        item_idx = 0
        while item_idx < len(student_items):
            item = student_items[item_idx]
            self._logger.debug(
                f"Processing student item {item_idx + 1}/{len(student_items)}"
            )
            try:
                # Extract basic student information using helper function
                student_name, class_name = self._extract_student_basic_info(
                    item, item_idx
                )

                # Skip if extraction failed
                if student_name is None or class_name is None:
                    continue

                # Get parent information
                self._logger.debug(
                    f"Getting parent info for item {item_idx + 1}, mock_parents={mock_parents}"
                )
                if mock_parents is True:
                    # Generate completely mock parent data
                    self._logger.debug(
                        f"Generating mock parents for item {item_idx + 1}"
                    )
                    num_parents = random.randint(1, 2)
                    from .mock import mock_parents as mock_parents_func

                    parents = mock_parents_func(num_parents)
                    self._logger.debug(
                        f"Generated {len(parents)} mock parents for item {item_idx + 1}"
                    )
                    # For mock parents, we don't need a real constituent ID
                    constituent_id = None
                else:
                    # For both mock parent-info and real scraping, get the constituent ID
                    # Parent names will be extracted in a separate pass
                    try:
                        profile_link = item.find_element(
                            By.CLASS_NAME, "fsConstituentProfileLink"
                        )
                        constituent_id = profile_link.get_attribute(
                            "data-constituent-id"
                        )
                        self._logger.debug(
                            f"Found constituent ID: {constituent_id} for {student_name}"
                        )
                    except Exception as e:
                        self._logger.warning(
                            f"Could not find constituent ID for {student_name}: {e}"
                        )
                        constituent_id = None

                    # Create placeholder parents - will be filled in second pass
                    parents = []

                student = {
                    "name": student_name,
                    "class": class_name,
                    "parents": parents,
                    "constituent_id": constituent_id,  # Store for later parent info extraction
                }

                students.append(student)
                self._logger.debug(
                    f"Found student: {student_name} in class: {class_name} with {len(parents)} parents"
                )

            except Exception as e:
                self._logger.warning(
                    f"Could not extract student info from item {item_idx + 1}: {e}"
                )

            # Move to next item
            item_idx += 1

        self._logger.info(f"Extracted {len(students)} students from page")
        return students

    def _extract_parent_names_for_page(self, students, mock_parents):
        """
        Extract parent names for all students on the current page.
        This should be called after basic student info has been collected.

        Args:
            students: List of student dictionaries with constituent_id
            mock_parents: Mock mode ("parent_info" for mock contact info, None/False for real)
        """
        self._logger.info(
            f"Extracting parent names for {len(students)} students on this page"
        )

        for student in students:
            try:
                constituent_id = student.get("constituent_id")
                if not constituent_id:
                    self._logger.debug(
                        f"No constituent ID for {student['name']}, skipping parent extraction"
                    )
                    continue

                # Find the student element using the constituent ID
                try:
                    student_element = self._driver.find_element(
                        By.CSS_SELECTOR, f"a[data-constituent-id='{constituent_id}']"
                    )
                    self._logger.debug(
                        f"Found student element for {student['name']} using ID {constituent_id}"
                    )
                except Exception as e:
                    self._logger.warning(
                        f"Could not find student element for {student['name']} with ID {constituent_id}: {e}"
                    )
                    continue

                # Get parent names for this student
                parent_names = self._get_student_parents(student_element)
                self._logger.debug(
                    f"Found {len(parent_names)} real parent names for {student['name']}: {parent_names}"
                )

                # Create parent objects with appropriate contact info
                parents = []
                for parent_name in parent_names:
                    if mock_parents == "parent_info":
                        # Generate mock contact info for each real parent
                        from .mock import mock_parents as mock_parents_func

                        mock_parent = mock_parents_func(1)[0]
                        parent = {
                            "name": parent_name,
                            "email": mock_parent["email"],
                            "phone": mock_parent["phone"],
                        }
                    else:
                        # Real scraping - contact info will be filled in next pass
                        parent = {
                            "name": parent_name,
                            "email": None,  # Will be filled in contact info pass
                            "phone": None,  # Will be filled in contact info pass
                        }
                    parents.append(parent)

                # Update the student with the parent information
                student["parents"] = parents

            except Exception as e:
                self._logger.error(
                    f"Error extracting parent names for {student['name']}: {e}"
                )
                continue

        self._logger.info("Finished extracting parent names for this page")

    def _extract_parent_contact_info_for_page(self, students):
        """
        Extract contact information for all parents on the current page.
        This should be called after parent names have been extracted.

        Args:
            students: List of student dictionaries with constituent_id and parents
        """
        self._logger.info(
            f"Extracting parent contact info for {len(students)} students on this page"
        )

        for student_idx, student in enumerate(students):
            try:
                # Get the stored constituent ID and find the current element
                constituent_id = student.get("constituent_id")
                if not constituent_id:
                    self._logger.warning(
                        f"No constituent ID stored for {student['name']}, skipping"
                    )
                    continue

                # Find the student element using the constituent ID
                try:
                    student_element = self._driver.find_element(
                        By.CSS_SELECTOR, f"a[data-constituent-id='{constituent_id}']"
                    )
                    self._logger.debug(
                        f"Found student element for {student['name']} using ID {constituent_id}"
                    )
                except Exception as e:
                    self._logger.warning(
                        f"Could not find student element for {student['name']} with ID {constituent_id}: {e}"
                    )
                    continue

                self._logger.info(f"Getting information for student {student['name']}")

                # Process each parent
                for parent_idx, parent in enumerate(student["parents"]):
                    try:
                        self._logger.info(
                            f"Getting information for parent {parent['name']} for student {student['name']}"
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

            # Get the target page number from the next page link
            target_page = next_page_link.get_attribute("data-page")
            self._logger.debug(f"Target page: {target_page}")

            # Get the name of the first student on the current page before navigation
            try:
                first_student_items = self._driver.find_elements(
                    By.CLASS_NAME, "fsConstituentItem"
                )
                if first_student_items:
                    first_name_elem = first_student_items[0].find_element(
                        By.CLASS_NAME, "fsFullName"
                    )
                    current_first_student_name = first_name_elem.text.strip()
                    self._logger.debug(
                        f"Current first student: '{current_first_student_name}'"
                    )
                else:
                    self._logger.warning("No student items found on current page")
                    current_first_student_name = None
            except Exception as e:
                self._logger.warning(f"Could not get current first student name: {e}")
                current_first_student_name = None

            # Use JavaScript click to bypass element interception issues
            self._logger.debug("Clicking next page link using JavaScript...")
            self._driver.execute_script("arguments[0].click();", next_page_link)
            self._logger.debug(f"Navigating to page {target_page}")

            # Wait for the first student name to change (indicating new page content)
            if current_first_student_name:
                WebDriverWait(self._driver, self.TIMEOUT).until(
                    lambda driver: self._get_first_student_name()
                    != current_first_student_name
                )
                new_first_student_name = self._get_first_student_name()
                self._logger.debug(
                    f"Page changed - new first student: '{new_first_student_name}'"
                )
            else:
                # Fallback: just wait for student items to be present
                WebDriverWait(self._driver, self.TIMEOUT).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "fsConstituentItem"))
                )
                self._logger.debug("Page navigation completed (fallback method)")

            self._logger.debug(f"Successfully navigated to page {target_page}")
            return True

        except NoSuchElementException:
            # No next page link found
            self._logger.debug("No next page link found")
            return False
        except Exception as e:
            self._logger.error(f"Error navigating to next page: {e}")
            return False

    def _get_first_student_name(self):
        """
        Helper method to get the name of the first student on the current page.

        Returns:
            str: Name of the first student, or None if not found
        """
        try:
            first_student_items = self._driver.find_elements(
                By.CLASS_NAME, "fsConstituentItem"
            )
            if first_student_items:
                first_name_elem = first_student_items[0].find_element(
                    By.CLASS_NAME, "fsFullName"
                )
                return first_name_elem.text.strip()
            return None
        except Exception:
            return None

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

            # Fetch basic student info from current page
            students_from_page = self._fetch_students_from_page(mock_parents=False)

            # Extract parent names for this page
            self._extract_parent_names_for_page(students_from_page, mock_parents=False)

            # Extract parent contact information for this page before moving to the next
            self._extract_parent_contact_info_for_page(students_from_page)

            class_students.extend(students_from_page)

            # Try to go to next page
            if not self._next_student_page():
                self._logger.debug(f"No more pages for class {class_name}")
                break

            page_num += 1

        # Clean up student objects by removing the stored constituent IDs
        for student in class_students:
            if "constituent_id" in student:
                del student["constituent_id"]

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

    def _get_class_student_info_with_mock_parent_info(self, class_name):
        """
        Get student information for a single class by scraping all pages, using real parent names
        but mock contact information.

        Args:
            class_name: Name of the class to scrape

        Returns:
            List of student dictionaries with name, class, and parents with mock contact info
        """
        self._logger.info(f"Processing class: {class_name} with mock parent info")

        # Select the class and wait for it to load
        self._select_class(class_name)

        class_students = []
        page_num = 1

        while True:
            self._logger.info(f"Fetching students from page {page_num}")

            # Fetch basic student info from current page
            students_from_page = self._fetch_students_from_page(
                mock_parents="parent_info"
            )

            # Extract parent names with mock contact info for this page
            self._extract_parent_names_for_page(
                students_from_page, mock_parents="parent_info"
            )

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
            elif mock == "parent-info":
                self._logger.info(
                    f"Scraping real student data with real parent names but mock contact info for classes: {classes}"
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
                    elif mock == "parent-info":
                        # Use real parent names with mock contact info
                        class_students = (
                            self._get_class_student_info_with_mock_parent_info(
                                class_name
                            )
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
