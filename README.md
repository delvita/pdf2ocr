# pdf2ocr Project

## Overview
The pdf2ocr project is a Flask-based application that utilizes Tesseract for Optical Character Recognition (OCR) to extract text from images. This project provides a simple interface for users to upload images and receive the extracted text.

## Project Structure
```
pdf2ocr
├── app.py                # Entry point of the application, starts the Flask server
├── requirements.txt      # Lists Python dependencies required for the project
├── Dockerfile            # Instructions for building the Docker image
├── src                   # Source code directory
│   ├── ocr.py           # Contains OCR processing logic
│   ├── api.py           # Defines API endpoints for the application
│   ├── utils.py         # Utility functions for image processing and file handling
│   └── templates
│       └── index.html   # HTML template for the user interface
├── tests                 # Directory for test files
│   └── test_ocr.py      # Tests for OCR functions
├── .devcontainer         # Development container configuration
│   └── devcontainer.json
├── docker-compose.yml    # Defines services needed for the application
├── .gitignore            # Files and directories to be ignored by Git
└── README.md             # Documentation for the project
```

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd pdf2ocr
   ```

2. Build the Docker image:
   ```
   docker build -t pdf2ocr .
   ```

3. Run the application using Docker Compose:
   ```
   docker-compose up
   ```

## Usage
- Access the application in your web browser at `http://localhost:5000`.
- Upload an image file to extract text using the OCR functionality.

## Testing
To run the tests for the OCR functions, navigate to the `tests` directory and execute:
```
pytest test_ocr.py
```

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License.