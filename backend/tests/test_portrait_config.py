from __future__ import annotations

from config import Settings
from core.image import PortraitImageService, VercelBlobStore
from schemas import PortraitStructuredPrompt


def test_settings_accept_common_hugging_face_aliases(monkeypatch) -> None:
    for env_name in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACEHUB_API_TOKEN", "HF_API_TOKEN"):
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setenv("HUGGING_FACE_HUB_TOKEN", "hf-alias-token")
    app_settings = Settings(_env_file=None)
    assert app_settings.hf_token == "hf-alias-token"


def test_settings_accept_common_blob_aliases(monkeypatch) -> None:
    for env_name in ("BLOB_READ_WRITE_TOKEN", "VERCEL_BLOB_READ_WRITE_TOKEN", "BLOB_TOKEN"):
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setenv("VERCEL_BLOB_READ_WRITE_TOKEN", "blob-alias-token")
    app_settings = Settings(_env_file=None)
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


async def test_hf_generation_uses_api_inference_endpoint(monkeypatch) -> None:
    """Ensure portrait generation calls api-inference.huggingface.co, not the router endpoint."""
    captured: dict[str, str] = {}

    class FakeResponse:
        is_success = True
        content = b"\x89PNG\r\n"
        headers = {"content-type": "image/png"}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url: str, **kwargs):
            captured["url"] = url
            return FakeResponse()

    monkeypatch.setattr("core.image.httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr("core.image.settings.hf_token", "hf-test-token")
    monkeypatch.setattr("core.image.settings.hf_image_model", "stabilityai/stable-diffusion-xl-base-1.0")
    monkeypatch.setattr("core.image.settings.has_blob_storage", False)

    prompt = PortraitStructuredPrompt(
        form_factor="abstract orb",
        expression_mood="curious",
        texture_material="glass",
        environment="void",
        lighting="bioluminescent",
        art_style="digital",
        camera_angle="front",
        composition_notes="centered",
        primary_colors=["#000"],
        accent_colors=["#fff"],
        symbolic_elements=["circle"],
    )
    await PortraitImageService()._generate_with_hugging_face(prompt)

    assert "router.huggingface.co/hf-inference/models" in captured["url"]
    assert "api-inference.huggingface.co" not in captured["url"]
    assert "stabilityai/stable-diffusion-xl-base-1.0" in captured["url"]
