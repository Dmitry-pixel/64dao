# -*- coding: utf-8 -*-
"""/uploads/images: картинки текста «О нас» отдаются, всё остальное нет.

Каталог uploads целиком наружу не монтируется (там токен банка и отчёты).
Монтирован только images/ и только файлы изображений.
"""
import uuid
from pathlib import Path

import pytest

from app.config import get_settings

IMAGES = Path(get_settings().uploads_dir).parent / "images"


@pytest.fixture
def files():
    IMAGES.mkdir(parents=True, exist_ok=True)
    stem = f"t-{uuid.uuid4().hex[:8]}"
    png, js = IMAGES / f"{stem}.png", IMAGES / f"{stem}.json"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    js.write_text('{"secret": 1}')
    secret = IMAGES.parent / f"{stem}-settings.json"
    secret.write_text('{"jwt": "x"}')
    yield stem
    for f in (png, js, secret):
        f.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_image_is_served(client, files):
    r = await client.get(f"/uploads/images/{files}.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"


@pytest.mark.asyncio
async def test_non_image_in_images_dir_is_hidden(client, files):
    assert (await client.get(f"/uploads/images/{files}.json")).status_code == 404


@pytest.mark.asyncio
async def test_parent_dir_is_not_reachable(client, files):
    assert (await client.get(f"/uploads/images/../{files}-settings.json")).status_code == 404
    assert (await client.get(f"/uploads/images/%2e%2e/{files}-settings.json")).status_code == 404
    assert (await client.get(f"/uploads/{files}-settings.json")).status_code == 404


@pytest.mark.asyncio
async def test_missing_image_404(client):
    assert (await client.get("/uploads/images/nope.png")).status_code == 404
