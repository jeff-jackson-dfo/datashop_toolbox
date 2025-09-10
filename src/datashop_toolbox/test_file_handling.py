import unittest
import tempfile
import os
from datashop_toolbox.validated_base import read_file_lines, find_lines_with_text

class TestFileHandlingFunctions(unittest.TestCase):

    def setUp(self):
        # Create a temporary file with sample content
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8')
        self.temp_file.write("Line one\nLine two with keyword\nLine three\nAnother keyword line\n")
        self.temp_file.close()
        self.file_path = self.temp_file.name

    def tearDown(self):
        # Remove the temporary file
        os.unlink(self.file_path)

    def test_read_file_lines_valid(self):
        lines = read_file_lines(self.file_path)
        self.assertIsInstance(lines, list)
        self.assertEqual(len(lines), 4)
        self.assertIn("Line one", lines)

    def test_read_file_lines_file_not_found(self):
        result = read_file_lines("non_existent_file.txt")
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith("File not found"))

    def test_read_file_lines_invalid_type(self):
        with self.assertRaises(TypeError):
            read_file_lines(123)  # Invalid type

    def test_find_lines_with_text_valid(self):
        lines = read_file_lines(self.file_path)
        matches = find_lines_with_text(lines, "keyword")
        self.assertEqual(len(matches), 2)
        self.assertTrue(all("keyword" in line for _, line in matches))

    def test_find_lines_with_text_invalid_lines_type(self):
        with self.assertRaises(TypeError):
            find_lines_with_text("not a list", "keyword")

    def test_find_lines_with_text_invalid_separator_type(self):
        lines = read_file_lines(self.file_path)
        with self.assertRaises(TypeError):
            find_lines_with_text(lines, 123)  # Invalid separator

if __name__ == "__main__":
    unittest.main()
