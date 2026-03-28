from __future__ import annotations

import base64
from dataclasses import dataclass
import logging
from urllib.parse import quote
from uuid import uuid4

import httpx
from vercel.blob import AsyncBlobClient

from config import settings
from abc import ABC, abstractmethod

from schemas import PortraitStructuredPrompt

logger = logging.getLogger(__name__)


@dataclass
class GeneratedImage:
    url: str
    source: str


class ImageGenerator(ABC):
    @abstractmethod
    async def generate(self, prompt: PortraitStructuredPrompt) -> GeneratedImage:
        raise NotImplementedError

    @abstractmethod
    async def upload(self, payload: bytes, content_type: str, filename_hint: str) -> GeneratedImage:
        raise NotImplementedError


class PlaceholderImageGenerator(ImageGenerator):
    async def generate(self, prompt: PortraitStructuredPrompt) -> GeneratedImage:
        primary = prompt.primary_colors[0] if prompt.primary_colors else "#1f2937"
        secondary = prompt.accent_colors[0] if prompt.accent_colors else "#ff7c64"
        tertiary = prompt.primary_colors[1] if len(prompt.primary_colors) > 1 else "#f4efe8"
        symbols = " ".join(prompt.symbolic_elements[:3]) or prompt.form_factor
        svg = f"""
        <svg xmlns='http://www.w3.org/2000/svg' width='768' height='1024' viewBox='0 0 768 1024'>
          <defs>
            <linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'>
              <stop offset='0%' stop-color='{primary}' />
              <stop offset='100%' stop-color='{secondary}' />
            </linearGradient>
          </defs>
          <rect width='768' height='1024' fill='#0b1016'/>
          <rect x='24' y='24' width='720' height='976' rx='42' fill='url(#bg)' opacity='0.78'/>
          <circle cx='384' cy='340' r='170' fill='{tertiary}' opacity='0.22'/>
          <circle cx='384' cy='340' r='116' fill='{secondary}' opacity='0.4'/>
          <rect x='142' y='560' width='484' height='210' rx='28' fill='#0b1016' opacity='0.58'/>
          <text x='384' y='610' text-anchor='middle' font-family='Georgia, serif' font-size='42' fill='#f8f2eb'>{prompt.form_factor}</text>
          <text x='384' y='668' text-anchor='middle' font-family='system-ui, sans-serif' font-size='24' fill='#f8f2eb'>{prompt.expression_mood}</text>
          <text x='384' y='728' text-anchor='middle' font-family='system-ui, sans-serif' font-size='20' fill='#f8f2eb'>{symbols}</text>
        </svg>
        """.strip()
        return GeneratedImage(url=f"data:image/svg+xml;charset=utf-8,{quote(svg)}", source="placeholder")

    async def upload(self, payload: bytes, content_type: str, filename_hint: str) -> GeneratedImage:
        encoded = base64.b64encode(payload).decode("ascii")
        return GeneratedImage(url=f"data:{content_type};base64,{encoded}", source="inline-upload")


class VercelBlobStore:
    async def put(self, payload: bytes, content_type: str, filename_hint: str) -> str:
        client = AsyncBlobClient(token=settings.blob_read_write_token)
        pathname = f"portraits/{uuid4().hex}-{filename_hint}"
        blob = await client.put(
            pathname,
            payload,
            access="public",
            add_random_suffix=False,
            content_type=content_type,
        )
        return blob.url


class PortraitImageService(ImageGenerator):
    def __init__(self) -> None:
        self.placeholder = PlaceholderImageGenerator()
        self.blob = VercelBlobStore()

    async def upload(self, payload: bytes, content_type: str, filename_hint: str) -> GeneratedImage:
        if settings.has_blob_storage:
            try:
                url = await self.blob.put(payload, content_type, filename_hint)
                return GeneratedImage(url=url, source="blob-upload")
            except Exception:
                logger.exception("Blob upload failed; falling back to inline portrait upload.")
        return await self.placeholder.upload(payload, content_type, filename_hint)

    async def _generate_with_hugging_face(self, prompt: PortraitStructuredPrompt) -> GeneratedImage:
        if not settings.hf_token:
            raise RuntimeError("HF_TOKEN is not configured.")

        prompt_text = " | ".join(
            [
                prompt.form_factor,
                f"mood: {prompt.expression_mood}",
                f"materials: {prompt.texture_material}",
                f"environment: {prompt.environment}",
                f"lighting: {prompt.lighting}",
                f"style: {prompt.art_style}",
                f"camera: {prompt.camera_angle}",
                f"composition: {prompt.composition_notes}",
                f"colors: {', '.join(prompt.primary_colors + prompt.accent_colors)}",
                f"symbols: {', '.join(prompt.symbolic_elements)}",
            ]
        )
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"https://api-inference.huggingface.co/models/{settings.hf_image_model}",
                headers={"Authorization": f"Bearer {settings.hf_token}"},
                json={
                    "inputs": prompt_text,
                    "parameters": {
                        "width": 768,
                        "height": 1024,
                        "num_inference_steps": 8,
                        "guidance_scale": 3.5,
                    },
                },
            )
        if not response.is_success:
            try:
                detail = response.json()
                reason = detail.get("error", response.text[:300])
            except Exception:
                reason = response.text[:300] or f"HTTP {response.status_code}"
            raise RuntimeError(f"Hugging Face API error ({response.status_code}): {reason}")
        return await self.upload(response.content, response.headers.get("content-type", "image/png"), "generated.png")

    async def generate(self, prompt: PortraitStructuredPrompt) -> GeneratedImage:
        if not settings.hf_token:
            raise RuntimeError(
                "Portrait generation is unavailable: HF_TOKEN is not configured. "
                "Copy the image prompt above and use it with Midjourney, DALL·E, Flux, or any image tool."
            )
        return await self._generate_with_hugging_face(prompt)
