from fastapi import Depends
from loguru import logger
from uuid import uuid4
from sqlalchemy import select, or_

from app.db.tables import Image, ImageStatus
from .base import BaseRepository


class ImageRepository(BaseRepository):
    base_table = Image

    async def create(self, **fields) -> Image:
        model = Image(**fields)
        return await self._create(model)

    async def update(self, image_id: str, **data) -> Image:
        if "is_finished" in data:
            value = data.pop("is_finished")
            data['status'] = ImageStatus.finished if value else ImageStatus.queued
        if "is_invalid" in data and data.pop("is_invalid"):
            data['status'] = ImageStatus.error

        return await self._update(image_id, write_none=True, **data)

    async def get(self, image_id: str) -> Image:
        return await self._get_one(id=image_id)

    async def list_in_progress(self) -> list[Image]:
        return list(await self._get_many(count=1000000, status=ImageStatus.queued))

