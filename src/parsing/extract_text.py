import json
from pathlib import Path
import fitz  # PyMuPDF

# Folder containing OCR'd PDFs
OCR_FOLDER = Path("data/ocr")

# Where extracted text will be saved
OUTPUT_JSON = Path("data/processed/extracted_text.json")


def extract_pdf_text(pdf_path):
    """
    Extract all text from a PDF.
    """

    document = fitz.open(pdf_path)

    text = ""

    for page in document:
        text += page.get_text()

    document.close()

    return text


def main():

    results = {}

    pdf_files = list(OCR_FOLDER.rglob("*_ocr.pdf"))

    print(f"Found {len(pdf_files)} OCR PDFs.\n")

    for index, pdf in enumerate(pdf_files, start=1):

        print(f"[{index}/{len(pdf_files)}] {pdf.name}")

        try:

            text = extract_pdf_text(pdf)

            results[str(pdf)] = {
                "filename": pdf.name,
                "text": text
            }

        except Exception as e:

            print(f"Failed: {pdf}")
            print(e)

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:

        json.dump(results, f, indent=4, ensure_ascii=False)

    print("\nFinished extracting text.")
    print(f"Saved to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()