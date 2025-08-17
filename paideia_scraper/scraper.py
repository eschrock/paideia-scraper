import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

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
            # TODO: Implement real scraping logic here using the classes parameter
            # For now, return empty list when not using mock data
            return []

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
