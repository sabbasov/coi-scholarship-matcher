from pathlib import Path
import hashlib
import json
from datetime import datetime

# Root folder containing scholarship files
RAW_FOLDER = Path("data/raw/ScholarshipFiles")

# Output JSON file
OUTPUT_JSON = Path("data/processed/deduplication_results.json")


def file_hash(filepath, chunk_size=8192):
    """
    Generate SHA256 hash for a file.
    """

    hasher = hashlib.sha256()

    with open(filepath, "rb") as f:

        while chunk := f.read(chunk_size):
            hasher.update(chunk)

    return hasher.hexdigest()


def get_modified_time(filepath):
    """
    Get file modification timestamp.
    """

    timestamp = filepath.stat().st_mtime

    return datetime.fromtimestamp(timestamp)


def scan_files(root_folder):
    """
    Recursively scan all files and group by hash.
    """

    file_groups = {}

    count = 0

    for filepath in root_folder.rglob("*"):

        if filepath.is_file():

            count += 1

            if count % 50 == 0:
                print(f"Processed {count} files")

            try:

                current_hash = file_hash(filepath)

                modified_time = get_modified_time(filepath)

                file_info = {
                    "path": str(filepath),
                    "modified_time": modified_time.isoformat(),
                }

                if current_hash not in file_groups:
                    file_groups[current_hash] = []

                file_groups[current_hash].append(file_info)

            except Exception as e:

                print(f"Error reading {filepath}: {e}")

    return file_groups


def select_latest_versions(file_groups):
    """
    Keep latest modified file as canonical version.
    Older copies become duplicates.
    """

    results = {}

    for file_hash_value, files in file_groups.items():

        # Sort newest first
        sorted_files = sorted(
            files,
            key=lambda x: x["modified_time"],
            reverse=True
        )

        latest_file = sorted_files[0]

        duplicates = sorted_files[1:]

        results[file_hash_value] = {
            "latest_version": latest_file,
            "duplicates": duplicates,
        }

    return results


def save_results(results, output_path):
    """
    Save deduplication results to JSON.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:

        json.dump(results, f, indent=4)

    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":

    print("Starting scholarship deduplication...\n")

    print(f"Folder exists: {RAW_FOLDER.exists()}")
    print(f"Scanning folder: {RAW_FOLDER}\n")

    grouped_files = scan_files(RAW_FOLDER)

    results = select_latest_versions(grouped_files)

    total_unique = len(results)

    total_duplicates = sum(
        len(v["duplicates"]) for v in results.values()
    )

    print("\n========== RESULTS ==========")

    print(f"Unique document groups: {total_unique}")
    print(f"Duplicate files found: {total_duplicates}")

    save_results(results, OUTPUT_JSON)