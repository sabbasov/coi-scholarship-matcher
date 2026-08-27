import subprocess
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]


def run_step(script_name: str) -> None:
    script_path = WORKSPACE_ROOT / "src" / "parsing" / script_name
    print(f"\n=== Running {script_name} ===")
    subprocess.run([sys.executable, str(script_path)], cwd=WORKSPACE_ROOT, check=True)


if __name__ == "__main__":
    run_step("deduplicate.py")
    run_step("ocr_pipeline.py")
    run_step("extract_text.py")
    print("\nPipeline completed successfully.")
