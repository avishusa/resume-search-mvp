import re
import unicodedata


PRIVATE_USE_RE = re.compile(r"[\ue000-\uf8ff]")
CONTROL_CHARACTER_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
REPLACEMENT_CHARACTER_RE = re.compile(r"[\ufffd\ufffe\uffff]")
REPEATED_SEPARATOR_RE = re.compile(r"([_\-=*•])(?:\s*\1){2,}")
LINE_SPACE_RE = re.compile(r"[ \t]+")
BLANK_LINE_RE = re.compile(r"\n{3,}")


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
