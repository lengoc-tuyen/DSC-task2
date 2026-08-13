import re
import unicodedata
from dataclasses import dataclass


_ARTICLE = re.compile(r"\bĐiều\s+(\d+[a-zđ]?)\b", re.IGNORECASE)
_CLAUSE = re.compile(r"\bkhoản\s+(\d+)\b", re.IGNORECASE)
_POINT = re.compile(r"\bđiểm\s+([a-zđ])\b", re.IGNORECASE)
_DOCUMENT = re.compile(r"\b\d{1,4}/\d{4}/[A-ZĐ0-9-]+\b", re.IGNORECASE)


@dataclass(frozen=True)
class QuestionAnalysis:
    original: str
    normalized: str
    search_text: str
    article_numbers: tuple[str, ...]
    clause_numbers: tuple[str, ...]
    point_labels: tuple[str, ...]
    document_numbers: tuple[str, ...]
    intent: str


def analyze_question(question: str) -> QuestionAnalysis:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")
    normalized = re.sub(r"\s+", " ", unicodedata.normalize("NFC", question)).strip()
    intent = _intent(normalized)
    documents = _unique(match.group(0) for match in _DOCUMENT.finditer(normalized))
    articles = _unique(match.group(1) for match in _ARTICLE.finditer(normalized))
    clauses = _unique(match.group(1) for match in _CLAUSE.finditer(normalized))
    points = _unique(match.group(1).casefold() for match in _POINT.finditer(normalized))
    hints = {"penalty": "mức phạt hình thức xử phạt biện pháp khắc phục", "procedure": "trình tự thủ tục hồ sơ", "deadline": "thời hạn thời gian", "eligibility": "điều kiện đối tượng"}.get(intent, "")
    search_text = f"{normalized} {hints}".strip()
    return QuestionAnalysis(question, normalized, search_text, articles, clauses, points, documents, intent)


def _intent(value: str) -> str:
    folded = value.casefold()
    if any(term in folded for term in ("xử phạt", "mức phạt", "phạt thế nào", "bị phạt")):
        return "penalty"
    if any(term in folded for term in ("thủ tục", "hồ sơ", "hướng dẫn")):
        return "procedure"
    if any(term in folded for term in ("thời hạn", "bao lâu", "thời gian")):
        return "deadline"
    if any(term in folded for term in ("điều kiện", "đối tượng nào")):
        return "eligibility"
    return "general"


def _unique(values):
    return tuple(dict.fromkeys(values))
