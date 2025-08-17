"""Mock data for testing the Paideia scraper output functionality."""

from faker import Faker

# Initialize Faker for generating realistic data
fake = Faker()


def mock_parents(num_parents):
    """
    Generate mock parent information for testing.

    Args:
        num_parents: Number of parents to generate

    Returns:
        List of parent dictionaries with name, email, and phone
    """
    parents = []

    for i in range(num_parents):
        # Generate realistic parent data
        parent = {
            "name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
        }
        parents.append(parent)

    return parents


def mock_student_name():
    """
    Generate a mock student name for testing.

    Returns:
        String containing a realistic student name
    """
    return fake.name()


# Generate mock students with dynamic parent data
MOCK_STUDENTS = [
    {"name": mock_student_name(), "class": "Kindergarten", "parents": mock_parents(2)},
    {"name": mock_student_name(), "class": "Kindergarten", "parents": mock_parents(1)},
    {"name": mock_student_name(), "class": "Kindergarten", "parents": mock_parents(2)},
    {"name": mock_student_name(), "class": "1st Grade", "parents": mock_parents(1)},
    {"name": mock_student_name(), "class": "1st Grade", "parents": mock_parents(1)},
    {"name": mock_student_name(), "class": "1st Grade", "parents": mock_parents(2)},
    {"name": mock_student_name(), "class": "2nd Grade", "parents": mock_parents(3)},
]
