import re
import unicodedata


PRIVATE_USE_RE = re.compile(r"[\ue000-\uf8ff]")
CONTROL_CHARACTER_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
REPLACEMENT_CHARACTER_RE = re.compile(r"[\ufffd\ufffe\uffff]")
REPEATED_SEPARATOR_RE = re.compile(r"([_\-=*•])(?:\s*\1){2,}")
LINE_SPACE_RE = re.compile(r"[ \t]+")
BLANK_LINE_RE = re.compile(r"\n{3,}")
SECTION_HEADING_ALIASES = [
    "skills",
    "technical skills",
    "work experience",
    "professional experience",
    "experience",
    "employment history",
    "education",
    "certifications",
]


def clean_resume_text_for_llm(resume_text: str) -> str:
    """Prepare extracted resume text for LLM parsing without changing stored text."""
    normalized_text = unicodedata.normalize("NFKC", resume_text)
    normalized_text = PRIVATE_USE_RE.sub(" ", normalized_text)
    normalized_text = REPLACEMENT_CHARACTER_RE.sub(" ", normalized_text)
    normalized_text = CONTROL_CHARACTER_RE.sub(" ", normalized_text)
    normalized_text = REPEATED_SEPARATOR_RE.sub(" ", normalized_text)

    cleaned_lines: list[str] = []
    for raw_line in normalized_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = LINE_SPACE_RE.sub(" ", raw_line).strip()
        if line:
            cleaned_lines.append(line)

    return BLANK_LINE_RE.sub("\n\n", "\n".join(cleaned_lines)).strip()


def build_resume_digest_for_llm(
    extracted_text: str,
    max_chars: int,
    top_chars: int = 3000,
    section_chunk_chars: int = 2200,
) -> str:
    """Build a compact resume digest that keeps high-value parsing sections."""
    cleaned_text = clean_resume_text_for_llm(extracted_text)
    if len(cleaned_text) <= max_chars:
        return cleaned_text

    chunks = [cleaned_text[: min(top_chars, max_chars)]]
    lines = cleaned_text.splitlines()

    for heading_index, _heading in _find_resume_section_headings(lines):
        chunk = _section_chunk(
            lines=lines,
            heading_index=heading_index,
            max_chars=section_chunk_chars,
        )
        if chunk:
            chunks.append(chunk)

    digest = _dedupe_digest_lines(chunks)
    return digest[:max_chars].strip()


def _find_resume_section_headings(lines: list[str]) -> list[tuple[int, str]]:
    headings: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        heading = _matching_section_heading(line)
        if heading:
            headings.append((index, heading))
    return headings


def _matching_section_heading(line: str) -> str | None:
    normalized_line = re.sub(r"[^a-zA-Z\s]", " ", line.lower())
    normalized_line = re.sub(r"\s+", " ", normalized_line).strip()
    if not normalized_line:
        return None

    for heading in SECTION_HEADING_ALIASES:
        if normalized_line == heading or normalized_line.startswith(f"{heading} "):
            return heading
    return None


def _section_chunk(
    lines: list[str],
    heading_index: int,
    max_chars: int,
) -> str:
    collected_lines: list[str] = []
    collected_chars = 0

    for line in lines[heading_index:]:
        if collected_lines and _matching_section_heading(line):
            next_heading_is_current = len(collected_lines) <= 1
            if not next_heading_is_current:
                break

        line_chars = len(line) + 1
        if collected_chars + line_chars > max_chars:
            break

        collected_lines.append(line)
        collected_chars += line_chars

    return "\n".join(collected_lines).strip()


def _dedupe_digest_lines(chunks: list[str]) -> str:
    seen_lines: set[str] = set()
    digest_lines: list[str] = []

    for chunk in chunks:
        for raw_line in chunk.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            dedupe_key = line.lower()
            if dedupe_key in seen_lines:
                continue
            seen_lines.add(dedupe_key)
            digest_lines.append(line)

    return "\n".join(digest_lines).strip()
