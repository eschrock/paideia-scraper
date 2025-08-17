from openpyxl import Workbook
from openpyxl.styles import Font


class Output:
    """Handles output operations for the Paideia scraper."""

    def __init__(self):
        """Initialize the Output class."""
        pass

    def write_excel(self, students, excel_path):
        """
        Write student data to an Excel file with separate sheets for each class.

        Args:
            students: List of student dictionaries with name, class, and parents
            excel_path: Path to the Excel file to create/overwrite
        """
        # Create a new workbook
        workbook = Workbook()

        # Remove the default sheet
        workbook.remove(workbook.active)

        # Group students by class
        class_data = {}

        for student in students:
            class_name = student["class"]
            student_name = student["name"]

            # Initialize class array if it doesn't exist
            if class_name not in class_data:
                class_data[class_name] = []

            # Add a row for each parent
            for parent in student["parents"]:
                row = [
                    student_name,  # Student
                    class_name,  # Class
                    parent["name"],  # Parent
                    parent["email"],  # Email
                    parent["phone"],  # Phone
                ]
                class_data[class_name].append(row)

        # Create a sheet for each class
        for class_name, rows in class_data.items():
            # Create worksheet
            worksheet = workbook.create_sheet(title=class_name)

            # Add header row
            headers = ["Student", "Class", "Parent", "Email", "Phone"]
            for col, header in enumerate(headers, 1):
                cell = worksheet.cell(row=1, column=col, value=header)
                cell.font = Font(bold=True)

            # Add data rows
            for row_idx, row_data in enumerate(rows, 2):
                for col_idx, value in enumerate(row_data, 1):
                    worksheet.cell(row=row_idx, column=col_idx, value=value)

        # Save the workbook
        workbook.save(excel_path)
