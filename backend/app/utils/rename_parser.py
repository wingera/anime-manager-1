import re
from pathlib import Path

ILLEGAL_NAME_CHARS = re.compile(r'[\\/:*?"<>|]')
VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".ts", ".m2ts", ".webm"}
SUBTITLE_EXTENSIONS = {".srt", ".ass", ".ssa", ".vtt", ".sub"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
DOCUMENT_EXTENSIONS = {".txt", ".nfo", ".pdf", ".doc", ".docx", ".md"}
EPISODE_PATTERNS = [
    re.compile(r"[Ss]\d{1,2}[Ee](\d{1,3})"),
    re.compile(r"第\s*(\d{1,3})\s*[集话話]"),
    re.compile(r"\bEP\s*0*(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"\bE\s*0*(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"\[\s*0*(\d{1,3})\s*\]"),
    re.compile(r"(?:^|[\s._-])0*(\d{1,3})(?:$|[\s._-])"),
]


def sanitize_name_part(value: str) -> str:
    cleaned = ILLEGAL_NAME_CHARS.sub("", value).strip()
    return re.sub(r"\s+", " ", cleaned)


def clean_title(title: str, remove_words: str = "") -> str:
    cleaned = title
    for word in _remove_word_list(remove_words):
        cleaned = cleaned.replace(word, "")
    cleaned = cleaned.replace(".", " ")
    return sanitize_name_part(cleaned)


def extract_episode_number(filename: str) -> int | None:
    stem = Path(filename).stem
    for pattern in EPISODE_PATTERNS:
        match = pattern.search(stem)
        if match:
            return int(match.group(1))
    return None


def classify_rename_file(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in SUBTITLE_EXTENSIONS:
        return "subtitle"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in DOCUMENT_EXTENSIONS:
        return "document"
    return "other"


def build_target_name(
    *,
    title: str,
    original_name: str,
    extension: str,
    episode_number: int | None,
    template: str,
    episode_padding: int,
    remove_words: str = "",
) -> str:
    clean = clean_title(title, remove_words)
    raw_episode = "" if episode_number is None else str(episode_number)
    episode = "" if episode_number is None else str(episode_number).zfill(episode_padding)
    rendered = template.format(
        title=sanitize_name_part(title),
        clean_title=clean,
        original_name=sanitize_name_part(original_name),
        episode=episode,
        episode_raw=raw_episode,
        ext=extension,
    )
    return sanitize_name_part(rendered)


def _remove_word_list(remove_words: str) -> list[str]:
    return [word.strip() for word in remove_words.split(",") if word.strip()]
