from __future__ import annotations

from config import Settings
from core.image import VercelBlobStore


def test_settings_accept_common_hugging_face_aliases(monkeypatch) -> None:
    for env_name in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACEHUB_API_TOKEN", "HF_API_TOKEN"):
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setenv("HUGGING_FACE_HUB_TOKEN", "hf-alias-token")
    app_settings = Settings()
    assert app_settings.hf_token == "hf-alias-token"


def test_settings_accept_common_blob_aliases(monkeypatch) -> None:
    for env_name in ("BLOB_READ_WRITE_TOKEN", "VERCEL_BLOB_READ_WRITE_TOKEN", "BLOB_TOKEN"):
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setenv("VERCEL_BLOB_READ_WRITE_TOKEN", "blob-alias-token")
    app_settings = Settings()
    assert app_settings.blob_read_write_token == "blob-alias-token"


async def test_blob_store_passes_token_to_client(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    class FakeBlob:
        url = "https://blob.example/portrait.png"

    class FakeAsyncBlobClient:
        def __init__(self, token: str | None = None):
            captured["token"] = token

        async def put(self, pathname, payload, **kwargs):
            return FakeBlob()

    monkeypatch.setattr("core.image.AsyncBlobClient", FakeAsyncBlobClient)
    monkeypatch.setattr("core.image.settings.blob_read_write_token", "blob-token")
    url = await VercelBlobStore().put(b"abc", "image/png", "portrait.png")

    assert captured["token"] == "blob-token"
    assert url == "https://blob.example/portrait.png"
