# Paideia Scraper

A web scraper for extracting student and parent information from the Paideia School parent portal.

## Prerequisites

Before using this scraper, you must have:

1. **Google Chrome browser** installed and updated to the latest version
2. **ChromeDriver** installed and matching your Chrome version

### Installing Chrome and ChromeDriver

#### Option 1: Homebrew (Recommended for macOS)

```bash
# Install Google Chrome
brew install --cask google-chrome

# Install ChromeDriver
brew install chromedriver

# Update ChromeDriver to match your Chrome version
brew upgrade chromedriver
```

#### Option 2: Manual Installation

1. **Download Chrome**: [https://www.google.com/chrome/](https://www.google.com/chrome/)
2. **Download ChromeDriver**: [https://chromedriver.chromium.org/downloads](https://chromedriver.chromium.org/downloads)
3. **Ensure versions match**: ChromeDriver version must support your Chrome browser version

## Configuration

The scraper can be configured in two ways:

### Option 1: JSON Configuration File (Recommended)

Create a `secrets/config.json` file in the project root:

```json
{
  "paideia_user": "your_username_here",
  "paideia_password": "your_password_here",
  "paideia_portal_url": "https://www.paideiaschool.org/pythons/parent-portal/"
}
```

**Note:** The `paideia_portal_url` field is optional and defaults to the URL shown above. The `secrets/` directory is automatically ignored by git to prevent accidentally committing sensitive information.

### Option 2: Environment Variables

Set the following environment variables:

- `PAIDEIA_USER`: Your Paideia School username
- `PAIDEIA_PASSWORD`: Your Paideia School password
- `PAIDEIA_PORTAL_URL`: (Optional) Custom portal URL

## Usage

Run the scraper with one or more class names as arguments:

```bash
python -m paideia_scraper.main "Class Name 1" "Class Name 2"
```

### Command Line Options

- `--debug`: Enable debug logging for detailed output
- `--login-only`: Only perform login, then exit (useful for testing credentials)
- `--mock TYPE`: Use mock data of specified type instead of scraping real data (mutually exclusive with other scraping options)
- `classes`: Class names to scrape (required unless --login-only or --mock is specified)

### Examples

Basic usage:

```bash
python -m paideia_scraper.main "Kindergarten" "1st Grade"
```

With debug logging:

```bash
python -m paideia_scraper.main --debug "Kindergarten" "1st Grade"
```

Test login only:

```bash
python -m paideia_scraper.main --login-only
```

Test login with debug logging:

```bash
python -m paideia_scraper.main --login-only --debug
```

Scrape all elementary school classes:

```bash
python -m paideia_scraper.main "Elementary School"
```

Scrape all elementary school classes with debug logging:

```bash
python -m paideia_scraper.main --debug "Elementary School"
```

Test with mock student data (still performs login):

```bash
python -m paideia_scraper.main --mock students
```

Test with mock student data and debug logging:

```bash
python -m paideia_scraper.main --mock students --debug
```

## Troubleshooting

### ChromeDriver Version Mismatch

If you see this error:

```
selenium.common.exceptions.SessionNotCreatedException: Message: session not created: This version of ChromeDriver only supports Chrome version X
Current browser version is Y
```

**Solution:**

```bash
# Update ChromeDriver to match your Chrome version
brew upgrade chromedriver

# Or reinstall if needed
brew uninstall chromedriver
brew install chromedriver
```

### ChromeDriver macOS Security Issue

If you encounter this error on macOS:

```
"chromedriver" Not Opened
Apple could not verify "chromedriver" is free of malware that may harm your Mac or compromise your privacy.
```

**Solution:**

1. Go to **System Preferences** → **Privacy & Security** → **General**
2. Look for a message about "chromedriver" being blocked
3. Click **"Allow Anyway"** or **"Open Anyway"**
4. Try running your scraper again

**Alternative Solutions:**

- Remove quarantine attribute: `xattr -d com.apple.quarantine $(which chromedriver)`
- Install via Homebrew: `brew install chromedriver`

## Output

The generated CSV file contains the following columns:

- Student: Student's name
- Class: Class name
- Parent: Parent's name
- Email: Parent's email address
- Phone: Parent's phone number

## Requirements

- Python 3.7+
- Google Chrome browser (latest version)
- ChromeDriver (matching Chrome version)
- Dependencies listed in `pyproject.toml`
