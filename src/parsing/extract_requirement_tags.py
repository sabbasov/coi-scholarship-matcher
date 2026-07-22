"""
ebonfowl:
Phase 1: Extract a general list of requirement tags for ALL scholarships.

This script:
1. Reads extracted scholarship text
2. Uses an LLM to identify all student requirements mentioned in each scholarship
3. Aggregates tags across all scholarships to create a comprehensive list

Input:  data/processed/extracted_text.json
Output: tags_list.json - Contains all unique requirement tags found across scholarships
"""

import json
import os
from pathlib import Path
from typing import Optional
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

# Input: extracted text from phase 0
EXTRACTED_TEXT_JSON = Path("data/processed/extracted_text.json")

# Output: comprehensive tag list
OUTPUT_TAGS_JSON = Path("data/processed/tags_list.json")

# Optional: path to file containing OpenAI API key
OPENAI_KEY_FILE = Path(".env.openai")


class RequirementTags(BaseModel):
    # Model for tags extracted from a scholarship
    scholarship_name: str
    tags: list[str]
    """
    List of requirement tags found (e.g., "GPA >= 3.0", "U.S. Citizen", 
    "Business Major", "First Generation", "Financial Need", etc.)
    """


def load_api_key():
    # Load OpenAI API key from environment or file.
    
    # Check if already set in environment
    if os.getenv("OPENAI_API_KEY"):
        return
    
    # Try to load from .env.openai file
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


def extract_tags_with_pydantic_ai(scholarship_name: str, text: str) -> list[str]:
    """
    ebonfowl:
    Use PydanticAI to extract requirement tags from scholarship text.
    
    Args:
        scholarship_name: Name of the scholarship
        text: Full text content of the scholarship document
        
    Returns:
        List of extracted requirement tags
    """
    
    agent = Agent(
        "openai:gpt-4o-mini",
        result_type=RequirementTags
    )
    
    prompt = f"""
    Analyze the following scholarship document and extract ALL student requirements 
    mentioned in the text. Focus on:
    - GPA requirements
    - Academic major/field of study
    - Residency or citizenship requirements
    - Grade level (freshman, sophomore, etc.)
    - Financial need status
    - Demographics (gender, ethnicity, first generation, etc.)
    - Military or veteran status
    - Work experience requirements
    - Essay or application requirements
    - Leadership or community service requirements
    - Specific achievements or awards
    - Any other academic or personal criteria
    
    Return tags as short, standardized phrases (e.g., "GPA >= 3.0", "US Citizen", 
    "Business Major", "Financial Need", "First Generation").
    
    Scholarship: {scholarship_name}
    
    Text:
    {text[:3000]}...
    """
    
    result = agent.run_sync(prompt)
    return result.data.tags


def extract_tags_with_openai(scholarship_name: str, text: str) -> list[str]:
    """
    ebonfowl:
    Fallback: Use OpenAI API directly to extract requirement tags.
    
    Args:
        scholarship_name: Name of the scholarship
        text: Full text content of the scholarship document
        
    Returns:
        List of extracted requirement tags
    """
    
    client = OpenAI()
    
    prompt = f"""
    Analyze the following scholarship document and extract ALL student requirements 
    mentioned in the text. Focus on:
    - GPA requirements
    - Academic major/field of study
    - Residency or citizenship requirements
    - Grade level (freshman, sophomore, etc.)
    - Financial need status
    - Demographics (gender, ethnicity, first generation, etc.)
    - Military or veteran status
    - Work experience requirements
    - Essay or application requirements
    - Leadership or community service requirements
    - Specific achievements or awards
    - Any other academic or personal criteria
    
    Return tags as short, standardized phrases (e.g., "GPA >= 3.0", "US Citizen", 
    "Business Major", "Financial Need", "First Generation").
    
    Scholarship: {scholarship_name}
    
    Text:
    {text[:3000]}...
    
    Return ONLY a JSON array of tags, nothing else. Example format:
    ["GPA >= 3.0", "Business Major", "Financial Need"]
    """
    
    message = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    response_text = message.choices[0].message.content
    tags = json.loads(response_text)
    return tags


def extract_tags(scholarship_name: str, text: str) -> list[str]:
    """
    ebonfowl:
    Extract requirement tags from scholarship text using available LLM.
    
    Args:
        scholarship_name: Name of the scholarship
        text: Full text content of the scholarship document
        
    Returns:
        List of extracted requirement tags
    """
    
    try:
        if HAS_PYDANTIC_AI:
            return extract_tags_with_pydantic_ai(scholarship_name, text)
        elif HAS_OPENAI:
            return extract_tags_with_openai(scholarship_name, text)
        else:
            raise ImportError("Neither pydantic-ai nor openai is installed")
    except Exception as e:
        print(f"Error extracting tags for {scholarship_name}: {e}")
        return []


def main():
    # Main function to extract tags from all scholarships.
    
    # Load API key before anything else
    load_api_key()
    
    # Check if LLM libraries are available
    if not HAS_PYDANTIC_AI and not HAS_OPENAI:
        print("ERROR: Neither pydantic-ai nor openai is installed.")
        print("Install one with:")
        print("  pip install pydantic-ai openai")
        print("  OR")
        print("  pip install openai")
        sys.exit(1)
    
    # Check if extracted text exists
    if not EXTRACTED_TEXT_JSON.exists():
        print(f"ERROR: {EXTRACTED_TEXT_JSON} not found.")
        print("Run extract_text.py first to generate extracted scholarship text.")
        sys.exit(1)
    
    # Load extracted text
    print("Loading extracted scholarship text...")
    with open(EXTRACTED_TEXT_JSON, "r", encoding="utf-8") as f:
        extracted_data = json.load(f)
    
    print(f"Found {len(extracted_data)} scholarships.\n")
    
    all_tags = set()
    scholarship_tags_mapping = {}
    
    # Process each scholarship
    for index, (file_path, file_info) in enumerate(extracted_data.items(), start=1):
        filename = file_info["filename"]
        text = file_info["text"]
        
        print(f"[{index}/{len(extracted_data)}] Processing: {filename}")
        
        # Clean up filename to get scholarship name
        scholarship_name = filename.replace("_ocr.pdf", "").replace("_", " ")
        
        # Extract tags
        tags = extract_tags(scholarship_name, text)
        
        if tags:
            all_tags.update(tags)
            scholarship_tags_mapping[scholarship_name] = tags
            print(f"  → Found {len(tags)} tags")
        else:
            print(f"  → No tags extracted")
    
    # Sort tags alphabetically
    sorted_tags = sorted(list(all_tags))
    
    # Prepare output
    output_data = {
        "total_scholarships": len(extracted_data),
        "total_unique_tags": len(sorted_tags),
        "tags": sorted_tags,
        "scholarship_mapping": scholarship_tags_mapping
    }
    
    # Save results
    OUTPUT_TAGS_JSON.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_TAGS_JSON, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    
    print(f"\n========== RESULTS ==========")
    print(f"Total scholarships processed: {len(extracted_data)}")
    print(f"Total unique tags extracted: {len(sorted_tags)}")
    print(f"\nFirst 20 tags:")
    for tag in sorted_tags[:20]:
        print(f"  - {tag}")
    if len(sorted_tags) > 20:
        print(f"  ... and {len(sorted_tags) - 20} more tags")
    
    print(f"\nResults saved to: {OUTPUT_TAGS_JSON}")


if __name__ == "__main__":
    main()