from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    status: str


class TextExtractor(Protocol):
    def extract(self, file_bytes: bytes) -> ExtractionResult:
        """Extract text from uploaded resume bytes."""
