import subprocess
import json
import os
import gzip
import sys
import importlib.util
from pathlib import Path

# Workspace root
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]

# JSON from deduplication step
DEDUP_JSON = WORKSPACE_ROOT / "data" / "processed" / "deduplication_results.json"

# OCR output folder
OUTPUT_FOLDER = WORKSPACE_ROOT / "data" / "ocr"
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

HAS_OCRMYPDF = importlib.util.find_spec("ocrmypdf") is not None


def process_pdf(input_pdf):
    input_pdf = Path(input_pdf)
    if not input_pdf.is_absolute():
        input_pdf = WORKSPACE_ROOT / input_pdf

    relative_path = Path(os.path.relpath(str(input_pdf), start=str(WORKSPACE_ROOT / "data" / "raw")))
    output_pdf = OUTPUT_FOLDER / relative_path
    output_pdf = output_pdf.with_name(f"{output_pdf.stem}_ocr.pdf")
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    if output_pdf.exists():
        print(f"Skipping (already OCR'd): {output_pdf.name}")
        return "skipped"

    if not HAS_OCRMYPDF:
        print(f"Skipping (ocrmypdf not installed): {input_pdf.name}")
        return "missing_dependency"

    try:
        subprocess.run(
            [
                sys.executable,
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
            text=True,
        )
        print(f"Done: {output_pdf.name}")
        return "processed"
    except ModuleNotFoundError:
        print("ocrmypdf is not installed. Install it with: pip install ocrmypdf")
        return "failed"
    except subprocess.CalledProcessError as e:
        print(f"Failed: {input_pdf.name}")
        if e.stderr:
            print(e.stderr)
        return "failed"


def main():
    print("Loading deduplication results...\n")

    if str(DEDUP_JSON).endswith(".gz") or DEDUP_JSON.suffix == ".gz":
        with gzip.open(DEDUP_JSON, "rt", encoding="utf-8") as f:
            dedup_data = json.load(f)
    else:
        with open(DEDUP_JSON, "r", encoding="utf-8") as f:
            dedup_data = json.load(f)

    latest_files = []
    for file_info in dedup_data.values():
        lv = file_info.get("latest_version", {})
        candidate = lv.get("full_path") or lv.get("path")

        if not candidate:
            continue

        p = Path(candidate)
        if not p.is_absolute():
            if (WORKSPACE_ROOT / p).exists():
                p = WORKSPACE_ROOT / p
            else:
                p = WORKSPACE_ROOT / "data" / "raw" / "ScholarshipFiles" / p

        if str(p).lower().endswith(".pdf"):
            latest_files.append(p)

    print(f"Found {len(latest_files)} unique PDFs to OCR.\n")

    processed = 0
    skipped = 0
    unavailable = 0
    failed = 0
    failed_files = []

    for index, pdf_path in enumerate(latest_files, start=1):
        print(f"\n[{index}/{len(latest_files)}] {Path(pdf_path).name}")
        result = process_pdf(pdf_path)

        if result == "processed":
            processed += 1
        elif result == "skipped":
            skipped += 1
        elif result == "missing_dependency":
            unavailable += 1
        elif result == "failed":
            failed += 1
            failed_files.append(str(pdf_path))

    print("\n========== OCR SUMMARY ==========")
    print(f"Processed : {processed}")
    print(f"Skipped   : {skipped}")
    print(f"Unavailable: {unavailable}")
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