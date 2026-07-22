"""
ebonfowl:
Phase 2: Match each scholarship to tags from a finalized, curated tag list.

This script:
1. Reads the curated/finalized tag list (manually edited from Phase 1 output)
2. Reads extracted scholarship text
3. Uses chatgpt to determine which tags from the finalized list apply to each scholarship
4. Outputs a structured JSON schema of scholarships to their matched tags

Input:  data/processed/tags_list_final.json  (manually curated from Phase 1)
        data/processed/extracted_text.json   (from extract_text.py)
Output: data/processed/scholarship_tag_matches.json
"""

import json
import os
from pathlib import Path
import sys

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

# Input: extracted scholarship text from extract_text.py
EXTRACTED_TEXT_JSON = Path("data/processed/extracted_text.json")

# Input: manually curated final tag list (edit tags_list.json from Phase 1 and save as this)
FINAL_TAGS_JSON = Path("data/processed/tags_list_final.json")

# Output: per-scholarship tag matches
OUTPUT_JSON = Path("data/processed/scholarship_tag_matches.json")

# Optional: path to file containing OpenAI API key
OPENAI_KEY_FILE = Path(".env.openai")


class ScholarshipTagMatch(BaseModel):
    # Matched tags for a single scholarship from the finalized tag list
    scholarship_name: str
    matched_tags: list[str]
    # Tags from the provided finalized list that apply to this scholarship
    notes: str
    # Any important caveats or ambiguities noted during matching


def load_api_key():
    # Load OpenAI API key from environment or file.

    if os.getenv("OPENAI_API_KEY"):
        return

    if OPENAI_KEY_FILE.exists():
        with open(OPENAI_KEY_FILE, "r") as f:
            api_key = f.read().strip()
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key
                print(f"Loaded OpenAI API key from {OPENAI_KEY_FILE}")
                return

    print("ERROR: OPENAI_API_KEY not found.")
    print(f"Set it in one of these ways:")
    print(f"  1. Environment variable: set OPENAI_API_KEY=your-key")
    print(f"  2. Create {OPENAI_KEY_FILE} file with your key")
    sys.exit(1)


def build_prompt(scholarship_name: str, text: str, tags: list[str]) -> str:
    # Build the matching prompt shared by both LLM paths.

    tags_formatted = "\n".join(f"  - {tag}" for tag in tags)

    # Let's do this with a functional string
    return f"""
You are reviewing a scholarship document to determine which student requirement tags apply.

Below is the COMPLETE list of allowed tags. You must ONLY return tags from this list — do not
invent new tags or rephrase existing ones.

ALLOWED TAGS:
{tags_formatted}

Now review this scholarship and return only the tags from the list above that are explicitly
stated or clearly implied by the document. If a requirement is not present, do not include
its tag.

Scholarship: {scholarship_name}

Document text:
{text[:4000]}
"""


def match_tags_with_pydantic_ai(
    scholarship_name: str, text: str, tags: list[str]
) -> ScholarshipTagMatch:
    # Use PydanticAI to match tags from the finalized list.

    agent = Agent("openai:gpt-4o-mini", result_type=ScholarshipTagMatch)
    result = agent.run_sync(build_prompt(scholarship_name, text, tags))
    return result.data


def match_tags_with_openai(
    scholarship_name: str, text: str, tags: list[str]
) -> ScholarshipTagMatch:
    # Use the OpenAI API directly to match tags from the finalized list.

    client = OpenAI()

    prompt = build_prompt(scholarship_name, text, tags) + """

Return a JSON object with exactly these two keys:
  "matched_tags": a JSON array of matched tag strings (only from the allowed list above)
  "notes": a string with any caveats or ambiguities, or "" if none

Example:
{
  "matched_tags": ["GPA >= 3.0", "Financial Need"],
  "notes": "GPA threshold was implied but not stated explicitly."
}
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


def match_tags(
    scholarship_name: str, text: str, tags: list[str]
) -> ScholarshipTagMatch:
    # Match tags using whichever LLM library is available.

    try:
        if HAS_PYDANTIC_AI:
            return match_tags_with_pydantic_ai(scholarship_name, text, tags)
        elif HAS_OPENAI:
            return match_tags_with_openai(scholarship_name, text, tags)
        else:
            raise ImportError("Neither pydantic-ai nor openai is installed")
    except Exception as e:
        print(f"  ! Error matching tags for {scholarship_name}: {e}")
        return ScholarshipTagMatch(
            scholarship_name=scholarship_name,
            matched_tags=[],
            notes=f"Error during processing: {e}",
        )


def main():
    # Main function to match finalized tags to each scholarship.

    load_api_key()

    # Check LLM libraries
    if not HAS_PYDANTIC_AI and not HAS_OPENAI:
        print("ERROR: Neither pydantic-ai nor openai is installed.")
        print("Install with:  pip install openai")
        sys.exit(1)

    # Check inputs exist
    for path in (EXTRACTED_TEXT_JSON, FINAL_TAGS_JSON):
        if not path.exists():
            print(f"ERROR: {path} not found.")
            if path == FINAL_TAGS_JSON:
                print(
                    "Create this file by copying data/processed/tags_list.json "
                    "(Phase 1 output), manually curating the tag list, and saving "
                    "it as tags_list_final.json."
                )
            else:
                print("Run extract_text.py first.")
            sys.exit(1)

    # Load finalized tag list
    print(f"Loading finalized tag list from {FINAL_TAGS_JSON}...")
    with open(FINAL_TAGS_JSON, "r", encoding="utf-8") as f:
        tags_data = json.load(f)

    # Support both a plain list and the Phase 1 JSON structure
    if isinstance(tags_data, list):
        final_tags = tags_data
    else:
        final_tags = tags_data.get("tags", [])

    print(f"Loaded {len(final_tags)} finalized tags.\n")

    # Load extracted scholarship text
    print(f"Loading extracted scholarship text from {EXTRACTED_TEXT_JSON}...")
    with open(EXTRACTED_TEXT_JSON, "r", encoding="utf-8") as f:
        extracted_data = json.load(f)

    print(f"Found {len(extracted_data)} scholarships.\n")

    results = {}

    for index, (file_path, file_info) in enumerate(extracted_data.items(), start=1):
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

        print(f"  → Matched {len(match.matched_tags)} tags")
        if match.notes:
            print(f"  ℹ {match.notes}")

    # Save output
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    # Summary
    total_matched = sum(len(v["matched_tags"]) for v in results.values())
    avg_matched = total_matched / len(results) if results else 0

    print(f"\n========== RESULTS ==========")
    print(f"Scholarships processed : {len(results)}")
    print(f"Total tag assignments  : {total_matched}")
    print(f"Avg tags per scholarship: {avg_matched:.1f}")
    print(f"\nResults saved to: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()