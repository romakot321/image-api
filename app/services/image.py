from fastapi import Depends, HTTPException
from uuid import UUID
from loguru import logger
import asyncio
import datetime as dt
import random

from app.repositories.ai import AIRepository
from app.repositories.image import ImageRepository
from app.schemas.image import ImageTaskCreateSchema, ImageTaskSchema
from app.schemas.ai import AIInputSchema, AIOutputSchema
from app.db.base import get_session
from app.db.tables import Image


class ImageService:
    def __init__(
            self,
            ai_repository: AIRepository = Depends(),
            image_repository: ImageRepository = Depends()
    ):
        self.ai_repository = ai_repository
        self.image_repository = image_repository

    async def create(self, schema: ImageTaskCreateSchema) -> ImageTaskSchema:
        model = await self.image_repository.create(
            user_id=schema.user_id,
            app_bundle=schema.app_bundle,
            prompt=schema.prompt,
            image_size=schema.image_size.value
        )
        return ImageTaskSchema.model_validate(model)

    async def _send(self, schema: ImageTaskCreateSchema, image_id: UUID):
        request = AIInputSchema(
            prompt=schema.prompt,
            image_size=schema.image_size.value,
            seed=random.randint(0, 999999999)
        )

        logger.debug("Sending submit request to AI: " + str(request.model_dump()))
        try:
            response = await self.ai_repository.submit(request, str(image_id))
            logger.debug("Received response: " + str(response))
        except TimeoutError:
            await self.image_repository.update(
                str(image_id),
                is_finished=False,
                is_invalid=True,
                comment="Timeout"
            )
            return schema
        except Exception as e:
            logger.exception(e)
            await self.image_repository.update(
                str(image_id),
                is_finished=False,
                is_invalid=True,
                comment=str(e)
            )
            return schema

        await self.image_repository.update(
            str(image_id),
            request_id=str(response),
            is_finished=False
        )

    async def store_ai_output(self, schema: AIOutputSchema, image_id: UUID):
        await self.image_repository.update(
            str(image_id),
            is_finished=True,
            image_url=schema.payload.images[0].url
        )

    async def get(self, image_id: UUID) -> ImageTaskSchema:
        model = await self.image_repository.get(str(image_id))
        return ImageTaskSchema.model_validate(model)

    async def _check(self, image: Image):
        if not image.request_id:
            return
        if not (await self.ai_repository.is_finished(image.request_id)):
            return
        result = await self.ai_repository.get_output(image.request_id)

        await self.image_repository.update(
            image.id,
            is_finished=True,
            is_invalid=False,
            image_url=result.images[0].url
        )

    @classmethod
    async def process_images_queue(cls):
        session_getter = get_session()
        db_session = await anext(session_getter)
        self = cls(ai_repository=AIRepository(), image_repository=ImageRepository(session=db_session))

        generating_count = await self.image_repository.count_generating_images()
        if generating_count >= 5:
            return
        images = await self.image_repository.list_unsended()
        if not images:
            return
        for image in images[:5 - generating_count]:
            schema = ImageTaskCreateSchema.model_validate(image)
            await self._send(schema, image.id)

        try:
            await anext(session_getter)
        except StopAsyncIteration:
            pass

    @classmethod
    async def update_images_status(cls):
        session_getter = get_session()
        db_session = await anext(session_getter)
        self = cls(ai_repository=AIRepository(), image_repository=ImageRepository(session=db_session))

        images = await self.image_repository.list_in_progress()
        check_tasks = [self._check(image) for image in images]
        await asyncio.gather(*check_tasks)

        try:
            await anext(session_getter)
        except StopAsyncIteration:
            pass

