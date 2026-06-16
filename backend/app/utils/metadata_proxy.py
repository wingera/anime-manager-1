from urllib.parse import quote

from app.db.models import AppSettings
from app.utils.secrets import decrypt_secret


def build_metadata_proxy_url(settings: AppSettings) -> str | None:
    proxy_type = settings.metadata_proxy_type or "none"
    if proxy_type == "none" or not settings.metadata_proxy_host or not settings.metadata_proxy_port:
        return None

    credentials = ""
    username = settings.metadata_proxy_username
    password = decrypt_secret(settings.metadata_proxy_password)
    if username:
        credentials = quote(username, safe="")
        if password:
            credentials = f"{credentials}:{quote(password, safe='')}"
        credentials = f"{credentials}@"

    return (
        f"{proxy_type}://"
        f"{credentials}{settings.metadata_proxy_host}:{settings.metadata_proxy_port}"
    )
