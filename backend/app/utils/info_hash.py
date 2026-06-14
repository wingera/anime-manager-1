import re

INFO_HASH_PATTERN = re.compile(r"(?<![0-9a-fA-F])([0-9a-fA-F]{40})(?![0-9a-fA-F])")


def normalize_info_hash(value: str) -> str:
    normalized = value.strip().lower()
    if INFO_HASH_PATTERN.fullmatch(normalized) is None:
        raise ValueError("资源指纹必须是 40 位十六进制字符串")
    return normalized


def build_magnet_uri(info_hash: str) -> str:
    return f"magnet:?xt=urn:btih:{normalize_info_hash(info_hash)}"


def find_info_hashes(text: str) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for match in INFO_HASH_PATTERN.finditer(text):
        info_hash = match.group(1).lower()
        if info_hash in seen:
            continue
        seen.add(info_hash)
        result.append(info_hash)
    return result
