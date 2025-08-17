"""Mock data for testing the Paideia scraper output functionality."""

MOCK_STUDENTS = [
    {
        "name": "Alice Johnson",
        "class": "Kindergarten",
        "parents": [
            {
                "name": "John Johnson",
                "email": "john.johnson@email.com",
                "phone": "555-0101",
            },
            {"name": "Mary Johnson", "email": "mary.johnson@email.com", "phone": None},
        ],
    },
    {
        "name": "Bob Smith",
        "class": "Kindergarten",
        "parents": [{"name": "Tom Smith", "email": None, "phone": "555-0201"}],
    },
    {
        "name": "Charlie Brown",
        "class": "Kindergarten",
        "parents": [
            {
                "name": "Frank Brown",
                "email": "frank.brown@email.com",
                "phone": "555-0301",
            },
            {
                "name": "Sally Brown",
                "email": "sally.brown@email.com",
                "phone": "555-0302",
            },
        ],
    },
    {
        "name": "Diana Prince",
        "class": "1st Grade",
        "parents": [
            {
                "name": "Steve Trevor",
                "email": "steve.trevor@email.com",
                "phone": "555-0401",
            }
        ],
    },
    {
        "name": "Eve Wilson",
        "class": "1st Grade",
        "parents": [{"name": "Bruce Wayne", "email": None, "phone": None}],
    },
    {
        "name": "Frank Miller",
        "class": "1st Grade",
        "parents": [
            {
                "name": "Clark Kent",
                "email": "clark.kent@email.com",
                "phone": "555-0601",
            },
            {"name": "Lois Lane", "email": "lois.lane@email.com", "phone": "555-0602"},
        ],
    },
]
