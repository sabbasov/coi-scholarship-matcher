"""
Phase 2: Match each scholarship to tags from a finalized, curated tag list.
"""

import json
import os
import sys
from pathlib import Path

try:
    from pydantic_ai import Agent
    from pydantic import BaseModel
    HAS_PYDANTIC_AI = True
except ImportError:
    HAS_PYDANTIC_AI = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# Workspace root
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]

# Input: extracted scholarship text from extract_text.py
EXTRACTED_TEXT_JSON = WORKSPACE_ROOT / "data" / "processed" / "extracted_text.json"

# Input: manually curated final tag list
FINAL_TAGS_JSON = WORKSPACE_ROOT / "data" / "processed" / "tags_list_final.json"

# Output: per-scholarship tag matches
OUTPUT_JSON = WORKSPACE_ROOT / "data" / "processed" / "scholarship_tag_matches.json"

# Optional: path to file containing OpenAI API key
OPENAI_KEY_FILE = WORKSPACE_ROOT / ".env.openai"


class ScholarshipTagMatch(BaseModel):
    scholarship_name: str
    matched_tags: list[str]
    notes: str


def load_api_key():
    if os.getenv("OPENAI_API_KEY"):
        return
    if OPENAI_KEY_FILE.exists():
        with open(OPENAI_KEY_FILE, "r", encoding="utf-8") as f:
            api_key = f.read().strip()
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key
                print(f"Loaded OpenAI API key from {OPENAI_KEY_FILE}")
                return
    print("ERROR: OPENAI_API_KEY not found.")
    sys.exit(1)


def build_prompt(scholarship_name: str, text: str, tags: list[str]) -> str:
    tags_formatted = "\n".join(f"  - {tag}" for tag in tags)
    return f"""
You are reviewing a scholarship document to determine which student requirement tags apply.

ALLOWED TAGS:
{tags_formatted}

Scholarship: {scholarship_name}

Document text:
{text[:4000]}
"""


def match_tags_with_pydantic_ai(scholarship_name: str, text: str, tags: list[str]) -> ScholarshipTagMatch:
    agent = Agent("openai:gpt-4o-mini", result_type=ScholarshipTagMatch)
    result = agent.run_sync(build_prompt(scholarship_name, text, tags))
    return result.data


def match_tags_with_openai(scholarship_name: str, text: str, tags: list[str]) -> ScholarshipTagMatch:
    client = OpenAI()
    prompt = build_prompt(scholarship_name, text, tags) + """

Return a JSON object with exactly these keys:
  "matched_tags": a JSON array of matched tag strings
  "notes": a string with caveats or ambiguities
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=1024,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    data = json.loads(response.choices[0].message.content)
    return ScholarshipTagMatch(
        scholarship_name=scholarship_name,
        matched_tags=data.get("matched_tags", []),
        notes=data.get("notes", ""),
    )


def match_tags(scholarship_name: str, text: str, tags: list[str]) -> ScholarshipTagMatch:
    try:
        if HAS_PYDANTIC_AI:
            return match_tags_with_pydantic_ai(scholarship_name, text, tags)
        elif HAS_OPENAI:
            return match_tags_with_openai(scholarship_name, text, tags)
        else:
            raise ImportError("Neither pydantic-ai nor openai is installed")
    except Exception as e:
        print(f"  ! Error matching tags for {scholarship_name}: {e}")
        return ScholarshipTagMatch(scholarship_name=scholarship_name, matched_tags=[], notes=f"Error during processing: {e}")


def main():
    load_api_key()
    if not HAS_PYDANTIC_AI and not HAS_OPENAI:
        print("ERROR: Neither pydantic-ai nor openai is installed.")
        sys.exit(1)

    for path in (EXTRACTED_TEXT_JSON, FINAL_TAGS_JSON):
        if not path.exists():
            print(f"ERROR: {path} not found.")
            sys.exit(1)

    with open(FINAL_TAGS_JSON, "r", encoding="utf-8") as f:
        tags_data = json.load(f)
    final_tags = tags_data if isinstance(tags_data, list) else tags_data.get("tags", [])

    with open(EXTRACTED_TEXT_JSON, "r", encoding="utf-8") as f:
        extracted_data = json.load(f)

    results = {}
    for index, (_, file_info) in enumerate(extracted_data.items(), start=1):
        filename = file_info["filename"]
        text = file_info["text"]
        scholarship_name = filename.replace("_ocr.pdf", "").replace("_", " ")
        print(f"[{index}/{len(extracted_data)}] {scholarship_name}")
        match = match_tags(scholarship_name, text, final_tags)
        results[scholarship_name] = {
            "matched_tags": match.matched_tags,
            "notes": match.notes,
            "source_file": filename,
        }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print(f"\nResults saved to: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()