from pathlib import Path

UNSAFE_PATH_MESSAGE = "文件路径不安全，已拒绝操作。"


def _is_inside(path: Path, base_dir: Path) -> bool:
    try:
        path.relative_to(base_dir)
    except ValueError:
        return False
    return True


def resolve_inside(base_dir: str, relative_path: str) -> Path:
    base = Path(base_dir).expanduser().resolve(strict=False)
    candidate = Path(relative_path)
    if candidate.is_absolute() or not relative_path.strip():
        raise ValueError(UNSAFE_PATH_MESSAGE)
    resolved = (base / candidate).resolve(strict=False)
    if not _is_inside(resolved, base):
        raise ValueError(UNSAFE_PATH_MESSAGE)
    return resolved


def ensure_target_inside(media_library_dir: str, target_path: str) -> Path:
    base = Path(media_library_dir).expanduser().resolve(strict=False)
    raw_target = Path(target_path)
    resolved = (
        raw_target.expanduser().resolve(strict=False)
        if raw_target.is_absolute()
        else (base / raw_target).resolve(strict=False)
    )
    if resolved == base or not _is_inside(resolved, base):
        raise ValueError(UNSAFE_PATH_MESSAGE)
    return resolved


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
