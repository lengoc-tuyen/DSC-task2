import re
from dataclasses import dataclass
from enum import Enum


class LineType(str, Enum):
    DOCUMENT_HEADER = "document_header"
    PART_HEADER = "part_header"
    CHAPTER = "chapter"
    SECTION = "section"
    ARTICLE = "article"
    CLAUSE = "clause"
    POINT = "point"
    BODY = "body"
    ADMINISTRATIVE_NOISE = "administrative_noise"


@dataclass(frozen=True)
class ReconstructedLine:
    text: str
    line_type: LineType
    start_offset: int
    end_offset: int


_PART = re.compile(r"^(?:QUY CHẾ|PHỤ LỤC|DANH MỤC|BIỂU MẪU)\b", re.IGNORECASE)
_CHAPTER = re.compile(r"^Chương\s+[IVXLCDM0-9]+\b", re.IGNORECASE)
_SECTION = re.compile(r"^(?:Mục|Tiểu mục)\s+[IVXLCDM0-9]+\b", re.IGNORECASE)
_ARTICLE = re.compile(r"^Điều\s+(\d+[a-zđ]?)\s*[.:]?\s*", re.IGNORECASE)
_CLAUSE = re.compile(r"^(\d+)\.\s+")
_POINT = re.compile(r"^([a-zđ])\)\s+", re.IGNORECASE)
_NOISE = re.compile(r"^Nơi nhận\s*:", re.IGNORECASE)


def classify_line(text: str, administrative: bool = False) -> LineType:
    if _PART.match(text) or re.match(r"^\(Ban hành kèm theo", text, re.IGNORECASE):
        return LineType.PART_HEADER
    if administrative or _NOISE.match(text):
        return LineType.ADMINISTRATIVE_NOISE
    if _CHAPTER.match(text):
        return LineType.CHAPTER
    if _SECTION.match(text):
        return LineType.SECTION
    if _ARTICLE.match(text):
        return LineType.ARTICLE
    if _CLAUSE.match(text):
        return LineType.CLAUSE
    if _POINT.match(text):
        return LineType.POINT
    if _looks_uppercase(text):
        return LineType.DOCUMENT_HEADER
    return LineType.BODY


def reconstruct_lines(text: str) -> tuple[ReconstructedLine, ...]:
    fragments = [fragment.strip() for fragment in re.split(r"\n+", text) if fragment.strip()]
    rebuilt: list[tuple[str, LineType]] = []
    administrative = False
    for fragment in fragments:
        standalone_type = classify_line(fragment)
        if administrative and standalone_type in {
            LineType.PART_HEADER, LineType.CHAPTER, LineType.SECTION, LineType.ARTICLE,
        }:
            administrative = False
        current_type = classify_line(fragment, administrative)
        if _NOISE.match(fragment):
            administrative = True
            current_type = LineType.ADMINISTRATIVE_NOISE
        if current_type == LineType.PART_HEADER:
            administrative = False
        if rebuilt and _should_join(rebuilt[-1], fragment, current_type):
            previous, previous_type = rebuilt[-1]
            combined = f"{previous} {fragment}"
            rebuilt[-1] = (combined, classify_line(combined, previous_type == LineType.ADMINISTRATIVE_NOISE))
        else:
            rebuilt.append((fragment, current_type))

    output: list[ReconstructedLine] = []
    cursor = 0
    for value, line_type in rebuilt:
        output.append(ReconstructedLine(value, line_type, cursor, cursor + len(value)))
        cursor += len(value) + 1
    return tuple(output)


def render_lines(lines: tuple[ReconstructedLine, ...]) -> str:
    return "\n".join(line.text for line in lines)


def _should_join(previous: tuple[str, LineType], current: str, current_type: LineType) -> bool:
    previous_text, previous_type = previous
    structural = {LineType.PART_HEADER, LineType.CHAPTER, LineType.SECTION, LineType.CLAUSE, LineType.POINT}
    if current_type in structural or current_type == LineType.ADMINISTRATIVE_NOISE:
        return False
    if previous_type in structural or previous_type == LineType.ADMINISTRATIVE_NOISE:
        return previous_type == LineType.ARTICLE and current_type == LineType.BODY
    if current_type == LineType.ARTICLE:
        return False
    if previous_type == LineType.ARTICLE:
        return True
    if previous_type == current_type == LineType.DOCUMENT_HEADER:
        return len(previous_text.split()) <= 5 and len(current.split()) <= 5
    return previous_type == LineType.BODY and current_type == LineType.BODY


def _looks_uppercase(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    return bool(letters) and all(char.isupper() for char in letters)


ARTICLE_PATTERN = _ARTICLE
