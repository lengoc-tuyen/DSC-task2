import re
import unicodedata
from collections import Counter

_IMPORTANT_TOKEN = re.compile(
    r"\b(?:không|trừ|ngoại trừ|Điều|Khoản|điểm)\b"
    r"|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
    r"|\b\d+(?:\.\d{3})+(?:,\d+)?\s*(?:đồng|VNĐ)?"
    r"|\b\d+(?:[.,]\d+)?%"
    r"|\b\d+[/-][A-ZĐ0-9-]+\b",
    re.IGNORECASE,
)


def normalize_passage(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\ufeff", "").replace("\u200b", "")
    normalized = normalized.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in normalized.split("\n")]
    return "\n".join(lines).strip()


def preservation_snapshot(text: str) -> Counter[str]:
    normalized = normalize_passage(text)
    return Counter(
        re.sub(r"\s+", " ", match.group(0)).strip().casefold()
        for match in _IMPORTANT_TOKEN.finditer(normalized)
    )
