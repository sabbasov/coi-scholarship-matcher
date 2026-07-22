"""
Phase 1: Extract a general list of requirement tags for ALL scholarships.
"""

import json
import os
import sys
import importlib
from dataclasses import dataclass
from pathlib import Path
from importlib.util import find_spec

HAS_PYDANTIC_AI = find_spec("pydantic_ai") is not None
HAS_OPENAI = find_spec("openai") is not None

# Workspace root
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]

# Input: extracted text from phase 0
EXTRACTED_TEXT_JSON = WORKSPACE_ROOT / "data" / "processed" / "extracted_text.json"

# Output: comprehensive tag list
OUTPUT_TAGS_JSON = WORKSPACE_ROOT / "data" / "processed" / "tags_list.json"

# Optional: paths that may contain the OpenAI API key
OPENAI_KEY_FILES = [
    WORKSPACE_ROOT / ".env.openai",
    Path(__file__).resolve().parent / ".env.openai",
]

# Prompting knobs
TEXT_CHUNK_SIZE = 8000

TAG_EXTRACTION_GUIDANCE = """
Extract short, standardized requirement tags only when they are explicit or strongly implied.
Good tags include examples like: GPA >= 3.0, Financial Need, Sophomore, Biology Major, U.S. Citizen, First Generation, Christian, Essay Required, Leadership, Community Service.
Avoid broad labels like Scholarship, Fund, or Agreement.
"""


@dataclass
class RequirementTags:
    scholarship_name: str
    tags: list[str]


def load_api_key():
    if os.getenv("OPENAI_API_KEY"):
        return
    for key_file in OPENAI_KEY_FILES:
        if key_file.exists():
            with open(key_file, "r", encoding="utf-8") as f:
                raw_value = f.read().strip()
                for line in raw_value.splitlines():
                    candidate = line.strip()
                    if not candidate or candidate.startswith("#"):
                        continue
                    if candidate.startswith("export "):
                        candidate = candidate[len("export "):].strip()
                    if candidate.startswith("OPENAI_API_KEY"):
                        _, sep, value = candidate.partition("=")
                        if sep:
                            candidate = value.strip()
                    candidate = candidate.strip().strip('"').strip("'")
                    if candidate:
                        os.environ["OPENAI_API_KEY"] = candidate
                        print(f"Loaded OpenAI API key from {key_file}")
                        return
    print("ERROR: OPENAI_API_KEY not found.")
    sys.exit(1)


def chunk_text(text: str, chunk_size: int = TEXT_CHUNK_SIZE) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start = end
    return chunks


def normalize_tags(raw_tags) -> list[str]:
    tags = []
    for tag in raw_tags or []:
        if not isinstance(tag, str):
            continue
        cleaned = tag.strip()
        if cleaned:
            tags.append(cleaned)
    return sorted(set(tags))


def extract_tags_with_pydantic_ai(scholarship_name: str, text: str) -> list[str]:
    agent_module = importlib.import_module("pydantic_ai")
    Agent = agent_module.Agent

    agent = Agent("openai:gpt-4o-mini", result_type=RequirementTags)
    tags = set()
    for index, chunk in enumerate(chunk_text(text), start=1):
        prompt = f"""
    {TAG_EXTRACTION_GUIDANCE}

    Scholarship: {scholarship_name}
    Chunk: {index}

    Text:
    {chunk}
    """
        result = agent.run_sync(prompt)
        tags.update(normalize_tags(result.data.tags))

    return sorted(tags)


def extract_tags_with_openai(scholarship_name: str, text: str) -> list[str]:
    openai_module = importlib.import_module("openai")
    OpenAI = openai_module.OpenAI

    client = OpenAI()
    tags = set()

    for index, chunk in enumerate(chunk_text(text), start=1):
        prompt = f"""
    {TAG_EXTRACTION_GUIDANCE}

    Scholarship: {scholarship_name}
    Chunk: {index}

    Text:
    {chunk}

    Return ONLY a JSON object with this shape:
    {{"tags": ["tag 1", "tag 2"]}}
    """
        message = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=1024,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.choices[0].message.content or "[]"
        try:
            parsed = json.loads(response_text)
            if isinstance(parsed, dict):
                tags.update(normalize_tags(parsed.get("tags", [])))
            elif isinstance(parsed, list):
                tags.update(normalize_tags(parsed))
        except json.JSONDecodeError:
            continue

    return sorted(tags)


def extract_tags(scholarship_name: str, text: str) -> list[str]:
    try:
        if HAS_OPENAI:
            return extract_tags_with_openai(scholarship_name, text)
        elif HAS_PYDANTIC_AI:
            return extract_tags_with_pydantic_ai(scholarship_name, text)
        else:
            raise ImportError("Neither pydantic-ai nor openai is installed")
    except Exception as e:
        print(f"Error extracting tags for {scholarship_name}: {e}")
        return []


def main():
    load_api_key()

    if not HAS_PYDANTIC_AI and not HAS_OPENAI:
        print("ERROR: Neither pydantic-ai nor openai is installed.")
        sys.exit(1)

    if not EXTRACTED_TEXT_JSON.exists():
        print(f"ERROR: {EXTRACTED_TEXT_JSON} not found. Run extract_text.py first.")
        sys.exit(1)

    print("Loading extracted scholarship text...")
    with open(EXTRACTED_TEXT_JSON, "r", encoding="utf-8") as f:
        extracted_data = json.load(f)

    print(f"Found {len(extracted_data)} scholarships.\n")

    all_tags = set()
    scholarship_tags_mapping = {}
    for index, (_, file_info) in enumerate(extracted_data.items(), start=1):
        filename = file_info["filename"]
        text = file_info["text"]
        scholarship_name = filename.replace("_ocr.pdf", "").replace("_", " ")

        print(f"[{index}/{len(extracted_data)}] Processing: {filename}")
        tags = extract_tags(scholarship_name, text)
        if tags:
            all_tags.update(tags)
            scholarship_tags_mapping[scholarship_name] = tags
            print(f"  → Found {len(tags)} tags")
        else:
            print("  → No tags extracted")

    sorted_tags = sorted(list(all_tags))
    output_data = {
        "total_scholarships": len(extracted_data),
        "total_unique_tags": len(sorted_tags),
        "tags": sorted_tags,
        "scholarship_mapping": scholarship_tags_mapping,
    }

    OUTPUT_TAGS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_TAGS_JSON, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)

    print(f"\n========== RESULTS ==========")
    print(f"Total scholarships processed: {len(extracted_data)}")
    print(f"Total unique tags extracted: {len(sorted_tags)}")
    print(f"\nResults saved to: {OUTPUT_TAGS_JSON}")


if __name__ == "__main__":
    main()