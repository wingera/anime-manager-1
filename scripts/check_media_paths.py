from __future__ import annotations

import os
from pathlib import Path


def check_path(path_text: str) -> tuple[bool, str]:
    path = Path(path_text)
    if not path.exists():
        return False, f"路径不存在：{path}"
    if not path.is_dir():
        return False, f"路径不是目录：{path}"
    if not os.access(path, os.R_OK):
        return False, f"路径不可读取：{path}"
    if not os.access(path, os.W_OK):
        return False, f"路径不可写入：{path}"
    return True, f"路径可用：{path}"


def main() -> None:
    targets = [
        os.getenv("DOWNLOAD_DIR", "./downloads"),
        os.getenv("MEDIA_LIBRARY_DIR", "./media"),
        os.getenv("DATA_DIR", "./data"),
    ]
    failed = False
    for target in targets:
        ok, message = check_path(target)
        print(message)
        failed = failed or not ok
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
