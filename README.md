# PDF Atelier

PDF Atelier is a Flask-based PDF utility app built from the original Python scripts in this project.

## Features

- Merge multiple PDF files into a single document
- Delete pages from a PDF using page numbers or ranges
- Extract selected pages into a new PDF
- Append pages from one PDF to another
- Convert one or more images into a PDF
- Generate QR codes as PDF sheets or PNG images
- Convert supported files such as images, TXT, MD, CSV, and JSON into PDF
- Enjoy a richer classic-inspired interface with images, sticker art, and animated GIF accents

## Run the app

1. Create and activate a virtual environment if you want one.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the Flask app:

```bash
python app.py
```

4. Open `http://127.0.0.1:5000`

## Notes

- Uploads are handled in temporary folders under `tmp/`.
- Page fields accept comma-separated page numbers and ranges such as `1, 3-5, 8`.
- The converter is intentionally limited to supported image and text-style files instead of claiming unlimited any-to-any conversion.
- The original CLI workflow still exists in `hello_pdf.py` and `pdf_merger.py`.
