from pathlib import Path

INVALID_FILENAME_CHARS = str.maketrans({char: "" for char in '/\\:*?"<>|'})


def sanitize_filename(value: str) -> str:
    cleaned = value.translate(INVALID_FILENAME_CHARS)
    return " ".join(cleaned.split()).strip() or "未命名"


def build_series_folder(title: str, year: int | None, tmdb_id: int | None) -> str:
    safe_title = sanitize_filename(title)
    year_part = f" ({year})" if year is not None else ""
    tmdb_part = f" [tmdbid={tmdb_id}]" if tmdb_id is not None else ""
    return f"{safe_title}{year_part}{tmdb_part}"


def build_season_folder(season_number: int | None) -> str:
    season = 1 if season_number is None else season_number
    return f"Season {season:02d}"


def build_episode_filename(
    title: str,
    season_number: int | None,
    episode_number: int | None,
    episode_title: str | None,
    extension: str,
) -> str:
    season = 1 if season_number is None else season_number
    episode = 1 if episode_number is None else episode_number
    safe_title = sanitize_filename(title)
    safe_episode_title = sanitize_filename(episode_title or f"第{episode}集")
    normalized_extension = extension if extension.startswith(".") else f".{extension}"
    return (
        f"{safe_title} - S{season:02d}E{episode:02d} - "
        f"{safe_episode_title}{normalized_extension}"
    )


def build_target_path(
    media_library_dir: str,
    title: str,
    year: int | None,
    tmdb_id: int | None,
    season_number: int | None,
    episode_number: int | None,
    episode_title: str | None,
    extension: str,
) -> str:
    return str(
        Path(media_library_dir)
        / build_series_folder(title, year, tmdb_id)
        / build_season_folder(season_number)
        / build_episode_filename(title, season_number, episode_number, episode_title, extension)
    )
