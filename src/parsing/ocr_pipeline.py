import subprocess
import json
from pathlib import Path

# JSON from deduplication step
DEDUP_JSON = Path("data/processed/deduplication_results.json")

# OCR output folder
OUTPUT_FOLDER = Path("data/ocr")
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)


def process_pdf(input_pdf):

    input_pdf = Path(input_pdf)

    # Preserve folder structure
    relative_path = input_pdf.relative_to("data/raw")

    output_pdf = OUTPUT_FOLDER / relative_path

    # Add _ocr suffix
    output_pdf = output_pdf.with_name(
        f"{output_pdf.stem}_ocr.pdf"
    )

    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    # Skip if OCR output already exists
    if output_pdf.exists():
        print(f"Skipping (already OCR'd): {output_pdf.name}")
        return "skipped"

    try:

        subprocess.run(
            [
                "python",
                "-m",
                "ocrmypdf",

                "--deskew",
                "--rotate-pages",
                "--skip-text",

                str(input_pdf),
                str(output_pdf),
            ],

            check=True,
            capture_output=True,
            text=True
        )

        print(f"Done: {output_pdf.name}")
        return "processed"

    except subprocess.CalledProcessError as e:

        print(f"Failed: {input_pdf.name}")
        print(e.stderr)

        return "failed"


def main():

    print("Loading deduplication results...\n")

    with open(DEDUP_JSON, "r", encoding="utf-8") as f:
        dedup_data = json.load(f)

    latest_files = []

    for file_info in dedup_data.values():

        latest_path = file_info["latest_version"]["path"]

        if latest_path.lower().endswith(".pdf"):
            latest_files.append(latest_path)

    print(f"Found {len(latest_files)} unique PDFs to OCR.\n")

    processed = 0
    skipped = 0
    failed = 0

    # Store failed file paths
    failed_files = []

    for index, pdf_path in enumerate(latest_files, start=1):

        print(f"\n[{index}/{len(latest_files)}] {Path(pdf_path).name}")

        result = process_pdf(pdf_path)

        if result == "processed":
            processed += 1

        elif result == "skipped":
            skipped += 1

        elif result == "failed":
            failed += 1
            failed_files.append(pdf_path)

    print("\n========== OCR SUMMARY ==========")
    print(f"Processed : {processed}")
    print(f"Skipped   : {skipped}")
    print(f"Failed    : {failed}")

    if failed_files:

        print("\n========== FAILED FILES ==========")

        for pdf in failed_files:
            print(pdf)

    else:
        print("\nNo failed files!")

    print("\nOCR pipeline complete.")


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()