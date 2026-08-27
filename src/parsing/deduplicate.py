from pathlib import Path
import hashlib
import json
import os
import gzip
import tempfile
from datetime import datetime, timezone

# Workspace root
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]

# Root folder containing scholarship files
RAW_FOLDER = WORKSPACE_ROOT / "data" / "raw" / "ScholarshipFiles"

# Output JSON file
OUTPUT_JSON = WORKSPACE_ROOT / "data" / "processed" / "deduplication_results.json"

# Behavior toggles
SKIP_HASH_FOR_SINGLETONS = True
COMPRESS_OUTPUT = False


def file_hash(filepath, chunk_size=8192):
    """Generate SHA256 hash for a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_modified_time(filepath):
    """Get a timezone-aware modification time."""
    timestamp = filepath.stat().st_mtime
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def scan_files(root_folder, skip_hash_singletons: bool = SKIP_HASH_FOR_SINGLETONS):
    """Recursively scan files, grouping by size first and hashing only likely matches."""
    file_stats = []
    errors = []
    count = 0

    for filepath in root_folder.rglob("*"):
        if not filepath.is_file():
            continue

        count += 1
        if count % 50 == 0:
            print(f"Processed {count} files")

        try:
            stat = filepath.stat()
            modified_dt = get_modified_time(filepath)
            file_stats.append(
                {
                    "path_obj": filepath,
                    "size": stat.st_size,
                    "modified_time": modified_dt.isoformat(),
                    "modified_ts": modified_dt.timestamp(),
                    "rel_path": filepath.relative_to(root_folder).as_posix(),
                    "full_path": filepath.resolve().as_posix(),
                }
            )
        except Exception as e:
            msg = f"Error reading metadata for {filepath}: {e}"
            print(msg)
            errors.append(msg)

    size_map = {}
    for info in file_stats:
        size_map.setdefault(info["size"], []).append(info)

    file_groups = {}
    for _, infos in size_map.items():
        if len(infos) == 1 and skip_hash_singletons:
            info = infos[0]
            key = f"SINGLE::{info['size']}::{int(info['modified_ts'])}::{Path(info['rel_path']).name}"
            file_groups.setdefault(key, []).append(
                {
                    "path": info["rel_path"],
                    "full_path": info["full_path"],
                    "modified_time": info["modified_time"],
                    "modified_ts": info["modified_ts"],
                }
            )
        else:
            for info in infos:
                try:
                    current_hash = file_hash(info["path_obj"])
                    file_groups.setdefault(current_hash, []).append(
                        {
                            "path": info["rel_path"],
                            "full_path": info["full_path"],
                            "modified_time": info["modified_time"],
                            "modified_ts": info["modified_ts"],
                        }
                    )
                except Exception as e:
                    msg = f"Error hashing {info['full_path']}: {e}"
                    print(msg)
                    errors.append(msg)

    return file_groups, errors


def select_latest_versions(file_groups):
    """Keep the newest modified file as the canonical version."""
    results = {}
    for file_hash_value, files in file_groups.items():
        sorted_files = sorted(files, key=lambda x: x.get("modified_ts", 0), reverse=True)
        latest_file = sorted_files[0]
        duplicates = sorted_files[1:]
        results[file_hash_value] = {"latest_version": latest_file, "duplicates": duplicates}
    return results


def save_results(results, output_path):
    """Save deduplication results to JSON, optionally as gzip."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if COMPRESS_OUTPUT:
        final_path = output_path.with_suffix(output_path.suffix + ".gz")
        with tempfile.NamedTemporaryFile(dir=output_path.parent, delete=False) as tf:
            with gzip.GzipFile(fileobj=tf, mode="wb") as gz:
                gz.write(json.dumps(results, indent=4).encode("utf-8"))
            tf.flush()
            os.fsync(tf.fileno())
            tmp_name = tf.name
        os.replace(tmp_name, final_path)
        print(f"\nResults saved to: {final_path}")
    else:
        with tempfile.NamedTemporaryFile(dir=output_path.parent, delete=False, mode="w", encoding="utf-8") as tf:
            json.dump(results, tf, indent=4)
            tf.flush()
            os.fsync(tf.fileno())
            tmp_name = tf.name
        os.replace(tmp_name, output_path)
        print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    print("Starting scholarship deduplication...\n")
    print(f"Folder exists: {RAW_FOLDER.exists()}")
    print(f"Scanning folder: {RAW_FOLDER}\n")

    grouped_files, errors = scan_files(RAW_FOLDER)
    if errors:
        print(f"\nEncountered {len(errors)} errors during scan.")

    results = select_latest_versions(grouped_files)
    total_unique = len(results)
    total_duplicates = sum(len(v["duplicates"]) for v in results.values())

    print("\n========== RESULTS ==========")
    print(f"Unique document groups: {total_unique}")
    print(f"Duplicate files found: {total_duplicates}")

    save_results(results, OUTPUT_JSON)