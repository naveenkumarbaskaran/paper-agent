"""PaperAgent — academic paper analysis with Claude."""

from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path
from typing import Any

import httpx

ARXIV_BASE = "https://export.arxiv.org/abs/"
ARXIV_API = "https://export.arxiv.org/api/query"

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert academic research assistant specialising in analysing
    scientific papers. Your role is to:

    1. Identify and clearly articulate the core problem a paper addresses.
    2. Summarise the methodology in plain, precise language.
    3. Extract quantitative and qualitative results.
    4. Note any limitations the authors acknowledge, plus any you observe.
    5. Generate a valid BibTeX citation entry.
    6. When comparing multiple papers, produce a structured comparison
       table covering problem, method, datasets, metrics, and findings.

    Always be factual. Quote numbers directly from the paper when available.
    When the paper text is truncated, reason from what is available.
""")

READ_PDF_TOOL: dict[str, Any] = {
    "name": "read_pdf_text",
    "description": (
        "Read and return the text content of a local PDF file. "
        "Use this when the user provides a file path ending in .pdf."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute or relative path to the PDF file.",
            }
        },
        "required": ["path"],
    },
}

FETCH_ARXIV_TOOL: dict[str, Any] = {
    "name": "fetch_arxiv",
    "description": (
        "Fetch the abstract and metadata of an arXiv paper by its ID "
        "(e.g. '2301.07041' or '2301.07041v2'). Returns title, authors, "
        "abstract, and a direct link."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "arxiv_id": {
                "type": "string",
                "description": "The arXiv paper identifier, e.g. '2301.07041'.",
            }
        },
        "required": ["arxiv_id"],
    },
}

WRITE_FILE_TOOL: dict[str, Any] = {
    "name": "write_file",
    "description": (
        "Write text content to a local file. "
        "Use this to save the final summary, comparison, or BibTeX output."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to write to (will be created or overwritten).",
            },
            "content": {
                "type": "string",
                "description": "Text content to write.",
            },
        },
        "required": ["path", "content"],
    },
}

ALL_TOOLS = [READ_PDF_TOOL, FETCH_ARXIV_TOOL, WRITE_FILE_TOOL]


def _tool_read_pdf_text(path: str) -> str:
    """Extract text from a local PDF."""
    from .pdf_reader import PdfReader

    try:
        reader = PdfReader(path)
        text = reader.extract_text()
        limit = 80_000
        if len(text) > limit:
            text = text[:limit] + "\n\n[... text truncated for context length ...]"
        return text
    except Exception as exc:
        return f"ERROR reading PDF: {exc}"


def _tool_fetch_arxiv(arxiv_id: str) -> str:
    """Fetch arXiv metadata via the public Atom API."""
    clean_id = arxiv_id.strip()
    clean_id = re.sub(r"^https?://arxiv\.org/(abs|pdf)/", "", clean_id)
    clean_id = clean_id.rstrip(".pdf")

    params = {"id_list": clean_id, "max_results": "1"}
    try:
        resp = httpx.get(ARXIV_API, params=params, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        return f"ERROR fetching arXiv paper: {exc}"

    xml = resp.text

    def _extract(tag: str) -> str:
        m = re.search(rf"<{tag}[^>]*>\s*(.*?)\s*</{tag}>", xml, re.DOTALL)
        return m.group(1).strip() if m else ""

    title = re.sub(r"\s+", " ", _extract("title"))
    summary = re.sub(r"\s+", " ", _extract("summary"))

    authors = re.findall(r"<name>([^<]+)</name>", xml)
    author_str = ", ".join(a.strip() for a in authors)

    published = _extract("published")[:10]
    year = published[:4] if published else "unknown"

    link_m = re.search(r'<id>(http[^<]+)</id>', xml)
    link = link_m.group(1).strip() if link_m else ARXIV_BASE + clean_id

    if not title or not summary:
        return f"ERROR: could not parse arXiv response for id '{clean_id}'."

    return (
        f"Title: {title}\n"
        f"Authors: {author_str}\n"
        f"Year: {year}\n"
        f"Published: {published}\n"
        f"Link: {link}\n\n"
        f"Abstract:\n{summary}"
    )


def _tool_write_file(path: str, content: str) -> str:
    """Write content to a file, creating parent directories if needed."""
    try:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        return f"OK — wrote {len(content)} characters to '{path}'."
    except Exception as exc:
        return f"ERROR writing file: {exc}"


def _dispatch_tool(name: str, tool_input: dict[str, Any]) -> str:
    """Route a tool-use call to the matching Python function."""
    if name == "read_pdf_text":
        return _tool_read_pdf_text(tool_input["path"])
    if name == "fetch_arxiv":
        return _tool_fetch_arxiv(tool_input["arxiv_id"])
    if name == "write_file":
        return _tool_write_file(tool_input["path"], tool_input["content"])
    return f"ERROR: unknown tool '{name}'."


class PaperAgent:
    """Academic paper analysis agent backed by Claude."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = MODEL,
        max_tokens: int = 8192,
    ) -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "anthropic is required: pip install anthropic"
            ) from exc

        self._anthropic = anthropic
        self.model = model
        self.max_tokens = max_tokens
        kwargs: dict[str, Any] = {}
        if api_key:
            kwargs["api_key"] = api_key
        self.client = anthropic.Anthropic(**kwargs)

    def analyze(
        self,
        source: str,
        output_path: str | None = None,
    ) -> str:
        is_pdf = source.lower().endswith(".pdf") or Path(source).suffix.lower() == ".pdf"
        if is_pdf:
            user_prompt = (
                f"Please analyse the paper at path '{source}'.\n\n"
                "Use the read_pdf_text tool to load it, then produce a structured "
                "summary with these sections:\n"
                "1. Problem Statement\n"
                "2. Methodology\n"
                "3. Results\n"
                "4. Limitations\n"
                "5. BibTeX entry\n\n"
                + (f"When done, save the summary to '{output_path}' using write_file." if output_path else "")
            )
        else:
            user_prompt = (
                f"Please analyse the arXiv paper with ID '{source}'.\n\n"
                "Use the fetch_arxiv tool to retrieve it, then produce a structured "
                "summary with these sections:\n"
                "1. Problem Statement\n"
                "2. Methodology\n"
                "3. Results\n"
                "4. Limitations\n"
                "5. BibTeX entry\n\n"
                + (f"When done, save the summary to '{output_path}' using write_file." if output_path else "")
            )

        return self._run_agentic_loop(user_prompt)

    def compare(
        self,
        sources: list[str],
        output_path: str | None = None,
    ) -> str:
        descriptions = []
        for s in sources:
            if s.lower().endswith(".pdf"):
                descriptions.append(f"PDF file at path '{s}'")
            else:
                descriptions.append(f"arXiv paper '{s}'")

        sources_text = "\n".join(f"- {d}" for d in descriptions)
        user_prompt = (
            f"Please compare the following {len(sources)} papers:\n{sources_text}\n\n"
            "For each paper use the appropriate tool (read_pdf_text or fetch_arxiv) "
            "to load its content, then produce:\n"
            "1. Individual summaries (Problem, Method, Results, Limitations) for each paper.\n"
            "2. A structured comparison table covering: Problem addressed, "
            "Methodology, Datasets/benchmarks, Key metrics, Main findings.\n"
            "3. A brief conclusion on how the approaches differ and which "
            "seems stronger for what use-case.\n"
            "4. BibTeX entries for all papers.\n\n"
            + (f"When done, save the comparison to '{output_path}' using write_file." if output_path else "")
        )

        return self._run_agentic_loop(user_prompt)

    def _run_agentic_loop(self, user_prompt: str) -> str:
        """Drive the tool-use loop until Claude produces a final answer."""
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_prompt}
        ]

        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                tools=ALL_TOOLS,
                messages=messages,
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                return self._collect_text(response.content)

            if response.stop_reason == "tool_use":
                tool_results: list[dict[str, Any]] = []
                for block in response.content:
                    if block.type == "tool_use":
                        result_text = _dispatch_tool(block.name, dict(block.input))
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result_text,
                            }
                        )
                if tool_results:
                    messages.append({"role": "user", "content": tool_results})
                continue

            return self._collect_text(response.content)

    @staticmethod
    def _collect_text(content: list[Any]) -> str:
        """Join all TextBlock values from a content list."""
        parts = []
        for block in content:
            if hasattr(block, "type") and block.type == "text":
                parts.append(block.text)
        return "\n\n".join(parts).strip()
