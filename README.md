# COI Scholarship Matcher

Pipeline for turning The College of Idaho scholarship archive into a searchable, AI-assisted dataset that can help financial aid staff identify scholarships by student parameters such as need, class standing, major, GPA, and other eligibility rules.

## What This Project Does

The original scholarship archive is a large collection of PDFs and related files stored across nested folders. This project converts that archive into structured data through a multi-stage pipeline:

1. **Deduplicate raw files** so the same scholarship agreement is not processed multiple times.
2. **OCR scanned PDFs** to create searchable, text-enabled documents.
3. **Extract document text** into JSON for downstream analysis.
4. **Identify requirement tags** from scholarship language using AI-assisted extraction.
5. **Match scholarships to curated tags** so future search and filtering tools can return relevant awards for a student profile.

## Current Status

The repository currently contains the full data-processing foundation for the matching system. The pipeline has already been used to process the scholarship archive and generate structured outputs for later search and interface work.

Current processed data includes:

- **636 scholarships** in the extracted tag dataset
- **966 unique requirement tags** discovered across the corpus

## Key Scripts

- `src/parsing/deduplicate.py` scans the raw archive, groups files by content, and records the latest version plus duplicates.
- `src/parsing/ocr_pipeline.py` runs OCR on PDF documents and writes searchable PDFs to `data/ocr`.
- `src/parsing/extract_text.py` extracts text from OCR'd PDFs and saves it to `data/processed/extracted_text.json`.
- `src/parsing/extract_requirement_tags.py` uses AI-assisted prompting to identify standardized scholarship requirement tags.
- `src/parsing/match_scholarship_tags.py` matches each scholarship against a curated final tag list.
- `src/parsing/run_pipeline.py` is the preferred entry point for the first three stages of the pipeline.

## What We Built

This project moved the work from an institutionally dependent spreadsheet workflow into a reproducible data pipeline. The resulting dataset makes it possible to search scholarship agreements by explicit requirements rather than by manual reading.

The pipeline also establishes the base for a second-stage application that could take a student profile and return scholarships that fit those parameters.

## What We Learned

- **Deduplication matters early.** Scholarship archives contain duplicates, backups, and revised agreements, so identifying the canonical version first prevents noisy downstream results.
- **Path handling needs to be workspace-aware.** The scripts resolve paths from the repository root so the pipeline works regardless of where it is launched.
- **OCR quality affects everything downstream.** Searchability and tag extraction depend on readable text, so preprocessing PDFs is a critical step.
- **Chunking improves LLM extraction.** Large scholarship agreements are broken into smaller chunks before tag extraction so model prompts stay manageable.
- **A curated tag taxonomy is essential.** Raw AI output can be broad or inconsistent, so standardized tags make the matching layer useful.
- **Modular scripts are easier to maintain.** Each stage can be rerun independently, which makes debugging and iteration much faster.

## How To Run

From the repository root:

```bash
python src/parsing/run_pipeline.py
```

To run stages individually:

```bash
python src/parsing/deduplicate.py
python src/parsing/ocr_pipeline.py
python src/parsing/extract_text.py
python src/parsing/extract_requirement_tags.py
python src/parsing/match_scholarship_tags.py
```

## Dependencies

The pipeline uses Python and a small set of optional libraries depending on which stage you run:

- `ocrmypdf` for OCR conversion
- `PyMuPDF` (`fitz`) for text extraction
- `pydantic-ai` or `openai` for AI-assisted tag extraction and matching

If you use the AI-assisted stages, set `OPENAI_API_KEY` or place a key in `.env.openai` as expected by the scripts.

## Project Structure

```text
data/
  raw/            Original scholarship archive
  ocr/            OCR-processed PDFs
  processed/      JSON outputs from deduplication, extraction, and tagging
src/
  parsing/        Pipeline scripts
```

## Next Step

The natural next phase is a search interface or lightweight application that accepts a student profile and returns matching scholarships from the tagged dataset.