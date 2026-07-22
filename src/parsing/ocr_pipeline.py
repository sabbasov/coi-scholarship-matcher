import subprocess
import json
import os
import gzip
from pathlib import Path

# Detect workspace root (3 levels up from this script: src/parsing/ocr_pipeline.py)
WORKSPACE_ROOT = Path(__file__).parent.parent.parent
DEDUP_JSON = WORKSPACE_ROOT / "data" / "processed" / "deduplication_results.json"

# OCR output folder (in workspace root)
OUTPUT_FOLDER = WORKSPACE_ROOT / "data" / "ocr"
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)


def process_pdf(input_pdf):

    input_pdf = Path(input_pdf)

    # Ensure input_pdf is absolute; if relative, resolve from workspace root
    if not input_pdf.is_absolute():
        input_pdf = WORKSPACE_ROOT / input_pdf

    # Preserve folder structure (relative to data/raw)
    relative_path = Path(os.path.relpath(str(input_pdf), start=str(WORKSPACE_ROOT / "data" / "raw")))

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
    # Support plain JSON or gzip-compressed JSON
    if str(DEDUP_JSON).endswith(".gz") or DEDUP_JSON.suffix == ".gz":
        with gzip.open(DEDUP_JSON, "rt", encoding="utf-8") as f:
            dedup_data = json.load(f)
    else:
        with open(DEDUP_JSON, "r", encoding="utf-8") as f:
            dedup_data = json.load(f)

    latest_files = []

    for file_info in dedup_data.values():
        lv = file_info.get("latest_version", {})

        # Prefer full_path when available
        if lv.get("full_path"):
            candidate = lv.get("full_path")
        else:
            candidate = lv.get("path")
            if candidate:
                candidate = str(Path("data/raw/ScholarshipFiles") / candidate)

        if not candidate:
            continue

        p = Path(candidate)

        # Resolve relative to workspace root if not absolute
        if not p.is_absolute():
            p = WORKSPACE_ROOT / p

        if str(p).lower().endswith(".pdf"):
            latest_files.append(p)

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