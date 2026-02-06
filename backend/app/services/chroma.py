from __future__ import annotations

import chromadb
from urllib.parse import urlparse

from app.core.config import get_settings

settings = get_settings()


def get_chroma_client() -> chromadb.ClientAPI:
    if settings.chroma_url:
        parsed = urlparse(settings.chroma_url)
        host = parsed.hostname or settings.chroma_url
        port = parsed.port or 8000
        return chromadb.HttpClient(host=host, port=port)
    return chromadb.Client()
