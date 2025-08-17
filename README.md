# Paideia Scraper

A web scraper for extracting student and parent information from the Paideia School parent portal.

## Configuration

The scraper can be configured in two ways:

### Option 1: JSON Configuration File (Recommended)

Create a `secrets/config.json` file in the project root:

```json
{
  "paideia_user": "your_username_here",
  "paideia_password": "your_password_here"
}
```

**Note:** The `secrets/` directory is automatically ignored by git to prevent accidentally committing sensitive information.

### Option 2: Environment Variables

Set the following environment variables:

- `PAIDEIA_USER`: Your Paideia School username
- `PAIDEIA_PASSWORD`: Your Paideia School password

## Usage

Run the scraper with one or more class names as arguments:

```bash
python -m paideia_scraper.main "Class Name 1" "Class Name 2"
```

The scraper will:

1. Log into the Paideia School parent portal
2. Extract student information for each specified class
3. Extract parent contact information for each student
4. Output the results to `output.csv`

## Output

The generated CSV file contains the following columns:

- Student: Student's name
- Class: Class name
- Parent: Parent's name
- Email: Parent's email address
- Phone: Parent's phone number

## Requirements

- Python 3.7+
- Chrome browser
- ChromeDriver (automatically managed by Selenium)
- Dependencies listed in `pyproject.toml`
