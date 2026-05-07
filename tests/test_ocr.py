import unittest
from src.ocr import process_image  # Assuming process_image is the function to test

class TestOCR(unittest.TestCase):

    def test_process_image_valid(self):
        # Test with a valid image file
        result = process_image('path/to/valid/image.png')
        self.assertIsInstance(result, str)  # Assuming the result is a string of extracted text

    def test_process_image_invalid(self):
        # Test with an invalid image file
        result = process_image('path/to/invalid/image.png')
        self.assertIsNone(result)  # Assuming the function returns None for invalid input

    def test_process_image_empty(self):
        # Test with an empty file
        result = process_image('path/to/empty/image.png')
        self.assertIsNone(result)  # Assuming the function returns None for empty input

if __name__ == '__main__':
    unittest.main()