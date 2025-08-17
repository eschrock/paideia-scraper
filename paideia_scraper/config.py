import json
import os
from pathlib import Path
import sys


class Config:
    def __init__(
        self, paideia_user: str, paideia_password: str, paideia_portal_url: str = None
    ):
        self.paideia_user = paideia_user
        self.paideia_password = paideia_password
        self.paideia_portal_url = (
            paideia_portal_url or "https://www.paideiaschool.org/pythons/parent-portal/"
        )


def load_config() -> Config:
    """
    Load configuration from secrets/config.json or environment variables.

    Returns:
        Config: Configuration object with paideia_user, paideia_password,
               and paideia_portal_url

    Raises:
        SystemExit: If neither config file nor environment variables are available
    """
    # First try to load from config file
    config_file = Path("secrets/config.json")

    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                config_data = json.load(f)

            paideia_user = config_data.get("paideia_user")
            paideia_password = config_data.get("paideia_password")
            paideia_portal_url = config_data.get("paideia_portal_url")

            if paideia_user and paideia_password:
                print(f"Loaded configuration from {config_file}")
                return Config(paideia_user, paideia_password, paideia_portal_url)
            else:
                print(f"Warning: {config_file} exists but missing required " "fields")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not read {config_file}: {e}")

    # Fall back to environment variables
    paideia_user = os.environ.get("PAIDEIA_USER")
    paideia_password = os.environ.get("PAIDEIA_PASSWORD")
    paideia_portal_url = os.environ.get("PAIDEIA_PORTAL_URL")

    if paideia_user and paideia_password:
        print("Loaded configuration from environment variables")
        return Config(paideia_user, paideia_password, paideia_portal_url)

    # Neither source available
    error_msg = (
        "Configuration not found. Please either:\n"
        "1. Create secrets/config.json with 'paideia_user' and "
        "'paideia_password' fields, or\n"
        "2. Set PAIDEIA_USER and PAIDEIA_PASSWORD environment variables"
    )
    print(error_msg, file=sys.stderr)
    sys.exit(1)
