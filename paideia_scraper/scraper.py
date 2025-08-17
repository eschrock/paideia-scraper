import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


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
