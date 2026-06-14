import re
from pathlib import Path

from app.utils.title_parser import guess_season_episode

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".ts", ".m2ts", ".webm"}
SUBTITLE_EXTENSIONS = {".srt", ".ass", ".ssa", ".vtt", ".sub"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DOCUMENT_EXTENSIONS = {".txt", ".nfo", ".url", ".html", ".htm", ".pdf"}
SAMPLE_KEYWORDS = ("sample", "preview", "trailer", "pv", "op", "ed")
MIN_MAIN_VIDEO_SIZE = 50 * 1024 * 1024
BARE_EPISODE_PATTERN = re.compile(r"(?<!\d)(\d{1,2})(?!\d)")


def _extension(name: str) -> str:
    return Path(name).suffix.lower()


def is_video_file(name: str) -> bool:
    return _extension(name) in VIDEO_EXTENSIONS


def is_subtitle_file(name: str) -> bool:
    return _extension(name) in SUBTITLE_EXTENSIONS


def is_sample_file(name: str, size: int) -> bool:
    if is_subtitle_file(name):
        return False
    lowered = Path(name).name.lower()
    if any(keyword in lowered for keyword in SAMPLE_KEYWORDS):
        return True
    return is_video_file(name) and size < MIN_MAIN_VIDEO_SIZE


def classify_file(name: str, size: int) -> str:
    extension = _extension(name)
    if is_sample_file(name, size):
        return "sample"
    if extension in VIDEO_EXTENSIONS:
        return "video"
    if extension in SUBTITLE_EXTENSIONS:
        return "subtitle"
    if extension in IMAGE_EXTENSIONS:
        return "image"
    if extension in DOCUMENT_EXTENSIONS:
        return "document"
    return "other"


def guess_episode_from_filename(name: str) -> tuple[int | None, int | None]:
    season_number, episode_number = guess_season_episode(name)
    if episode_number is not None:
        return season_number, episode_number

    stem = Path(name).stem
    for match in reversed(list(BARE_EPISODE_PATTERN.finditer(stem))):
        value = int(match.group(1))
        if 1 <= value <= 99:
            return None, value
    return None, None


def score_download_file(name: str, size: int) -> int:
    file_type = classify_file(name, size)
    score = {
        "video": 70,
        "subtitle": 50,
        "sample": 15,
        "image": 10,
        "document": 5,
        "other": 0,
    }[file_type]
    season_number, episode_number = guess_episode_from_filename(name)
    if season_number is not None:
        score += 10
    if episode_number is not None:
        score += 20
    if file_type == "video" and size >= MIN_MAIN_VIDEO_SIZE:
        score += 10
    return min(score, 100)
