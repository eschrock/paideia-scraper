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

    def _fetch_students_from_page(self):
        """
        Fetch student information from the current page.

        Returns:
            List of student dictionaries with name and class
        """
        students = []

        # Find all student item containers
        student_items = self._driver.find_elements(By.CLASS_NAME, "fsConstituentItem")

        for item in student_items:
            try:
                # Wait for student name to be populated
                name_elem = WebDriverWait(item, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "fsFullName"))
                )

                # Wait for the name text to be non-empty
                WebDriverWait(item, 10).until(lambda x: name_elem.text.strip() != "")

                student_name = name_elem.text.strip()

                # Skip students with empty names (shouldn't happen now, but safety check)
                if not student_name:
                    continue

                # Wait for location to be populated
                location_elem = WebDriverWait(item, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "fsLocations"))
                )

                # Wait for the location text to be non-empty
                WebDriverWait(item, 10).until(
                    lambda x: location_elem.text.strip() != ""
                )

                location_text = location_elem.text.strip()

                # Take only the part before the first comma
                class_name = location_text.split(",")[0].strip()

                student = {"name": student_name, "class": class_name}

                students.append(student)
                self._logger.debug(
                    f"Found student: {student_name} in class: {class_name}"
                )

            except Exception as e:
                self._logger.warning(f"Could not extract student info from item: {e}")
                continue

        self._logger.info(f"Extracted {len(students)} students from page")
        return students

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

            # Fetch students from current page
            students_from_page = self._fetch_students_from_page()

            # Add mock parent information to each student
            for student in students_from_page:
                # Generate random number of parents (1-2)
                num_parents = random.randint(1, 2)
                from .mock import mock_parents

                student["parents"] = mock_parents(num_parents)
                class_students.append(student)

                self._logger.debug(
                    f"Added student {student['name']} with {num_parents} parents"
                )

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
            self._logger.info(f"Scraping real data for classes: {classes}")

            all_students = []

            for class_name in classes:
                try:
                    # Get student info for this class (always loops through pages)
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
