# paper-agent-ai

AI-powered academic paper analysis using [Claude](https://www.anthropic.com/claude).
Analyse single papers or compare multiple papers side-by-side — from local PDF files
or directly from arXiv.

## Features

- **Structured analysis** — Problem Statement, Methodology, Results, Limitations, BibTeX
- **Multi-paper comparison** — side-by-side comparison table with a final verdict
- **PDF support** — local PDF files via `pypdf`
- **arXiv support** — fetch papers by ID directly from the arXiv API
- **File output** — save any result to a Markdown file with `--output`
- **Rich terminal UI** — progress spinners and rendered Markdown output

## Installation

```bash
pip install paper-agent-ai
```

Or from source:

```bash
git clone https://github.com/your-org/paper-agent-ai
cd paper-agent-ai
pip install -e .
```

## Quick Start

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Analyse a PDF

```bash
paper-agent analyze paper.pdf
paper-agent analyze paper.pdf --output summary.md
```

### Analyse an arXiv paper

```bash
paper-agent analyze 2301.07041
paper-agent analyze 2301.07041 --output summary.md
```

### Compare papers

```bash
# Two PDFs
paper-agent compare paper1.pdf paper2.pdf

# Two arXiv papers
paper-agent compare 2301.07041 2305.12345

# Mixed sources
paper-agent compare paper1.pdf 2305.12345 --output comparison.md

# Three or more papers
paper-agent compare 2301.07041 2305.12345 2307.09288
```

## Python API

```python
from paper_agent import PaperAgent

agent = PaperAgent()  # reads ANTHROPIC_API_KEY from environment

# Analyse a single paper
summary = agent.analyze("paper.pdf", output_path="summary.md")
print(summary)

# Analyse an arXiv paper
summary = agent.analyze("2301.07041")
print(summary)

# Compare multiple papers
comparison = agent.compare(
    ["paper1.pdf", "2305.12345"],
    output_path="comparison.md",
)
print(comparison)
```

### PaperAgent constructor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str \| None` | `None` | Anthropic API key; reads `ANTHROPIC_API_KEY` if `None` |
| `model` | `str` | `"claude-sonnet-4-6"` | Claude model identifier |
| `max_tokens` | `int` | `8192` | Maximum tokens per response turn |

## How it works

`PaperAgent` drives a **tool-use agentic loop** against the Claude API:

1. A user prompt describing the task is sent to Claude along with three tools.
2. Claude calls tools as needed:
   - `read_pdf_text(path)` — extracts and cleans text from a local PDF via `pypdf`
   - `fetch_arxiv(arxiv_id)` — fetches title, authors, abstract from the arXiv Atom API
   - `write_file(path, content)` — saves the final output to disk
3. Each tool result is fed back to Claude in the next turn.
4. The loop continues until Claude returns `stop_reason="end_turn"`.

## PDF Reader

`PdfReader` can be used standalone:

```python
from paper_agent import PdfReader

reader = PdfReader("paper.pdf")
text = reader.extract_text()  # cleaned text string
```

Cleaning steps applied:
- Remove lone page-number lines
- Remove table-separator lines (dashes, dots)
- Collapse runs of blank lines
- Normalise internal whitespace

## Dependencies

| Package | Purpose |
|---------|--------|
| `anthropic` | Claude API client |
| `click` | CLI framework |
| `rich` | Terminal formatting and Markdown rendering |
| `httpx` | HTTP client for the arXiv API |
| `pypdf` | PDF text extraction |

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Licence

MIT
