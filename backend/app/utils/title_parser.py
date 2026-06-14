import re

YEAR_PATTERN = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")
SXX_EXX_PATTERN = re.compile(r"\bs(?:eason\s*)?0*(\d{1,2})\s*e(?:pisode\s*)?0*(\d{1,3})\b", re.I)
CHINESE_SEASON_EPISODE_PATTERN = re.compile(r"第\s*(\d{1,2})\s*季\s*第\s*(\d{1,3})\s*集")
ENGLISH_SEASON_EPISODE_PATTERN = re.compile(
    r"\bseason\s*0*(\d{1,2})\s*episode\s*0*(\d{1,3})\b",
    re.I,
)
BRACKET_PATTERN = re.compile(r"[\[\]【】()（）]")
HASH_LIKE_PATTERN = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{40}(?![0-9a-fA-F])")


def guess_year(title: str) -> int | None:
    match = YEAR_PATTERN.search(title)
    return int(match.group(1)) if match else None


def guess_season_episode(title: str) -> tuple[int | None, int | None]:
    for pattern in (
        SXX_EXX_PATTERN,
        CHINESE_SEASON_EPISODE_PATTERN,
        ENGLISH_SEASON_EPISODE_PATTERN,
    ):
        match = pattern.search(title)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None, None


def clean_search_title(title: str) -> str:
    cleaned = HASH_LIKE_PATTERN.sub(" ", title)
    for pattern in (
        SXX_EXX_PATTERN,
        CHINESE_SEASON_EPISODE_PATTERN,
        ENGLISH_SEASON_EPISODE_PATTERN,
        YEAR_PATTERN,
    ):
        cleaned = pattern.sub(" ", cleaned)
    cleaned = BRACKET_PATTERN.sub(" ", cleaned)
    return " ".join(cleaned.split())
