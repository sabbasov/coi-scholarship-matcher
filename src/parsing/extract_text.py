import json
from pathlib import Path
import fitz  # PyMuPDF

# Workspace root
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]

# Folder containing OCR'd PDFs
OCR_FOLDER = WORKSPACE_ROOT / "data" / "ocr"

# Where extracted text will be saved
OUTPUT_JSON = WORKSPACE_ROOT / "data" / "processed" / "extracted_text.json"


def extract_pdf_text(pdf_path):
    """Extract all text from a PDF."""
    document = fitz.open(pdf_path)
    text = ""
    for page in document:
        text += page.get_text()
    document.close()
    return text


def main():
    results = {}
    pdf_files = sorted(OCR_FOLDER.rglob("*_ocr.pdf"))

    if not pdf_files:
        print("No OCR PDFs were found. Run ocr_pipeline.py first or place *_ocr.pdf files under data/ocr.")
        OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        print(f"Saved empty result to {OUTPUT_JSON}")
        return

    print(f"Found {len(pdf_files)} OCR PDFs.\n")

    for index, pdf in enumerate(pdf_files, start=1):
        print(f"[{index}/{len(pdf_files)}] {pdf.name}")
        try:
            text = extract_pdf_text(pdf)
            results[str(pdf.relative_to(WORKSPACE_ROOT))] = {
                "filename": pdf.name,
                "text": text,
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