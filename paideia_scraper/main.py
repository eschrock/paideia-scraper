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

from paideia_scraper.config import load_config
from paideia_scraper.scraper import Scraper
from paideia_scraper.output import Output


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
        choices=["students", "parents", "parent-info"],
        help=(
            "Use mock data of specified type (can be combined with class names). "
            "'parent-info' uses real parent names but mock contact info."
        ),
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


if __name__ == "__main__":
    sys.exit(main())
