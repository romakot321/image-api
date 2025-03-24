from fastapi import Depends, HTTPException
from uuid import UUID
from loguru import logger
import asyncio
import datetime as dt
import random
import io

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
            image_size=schema.image_size
        )
        return ImageTaskSchema.model_validate(model)

    async def create_img2img(self, schema: ImageTaskCreateSchema, image_body: io.BytesIO) -> ImageTaskSchema:
        image_url = await self.ai_repository.upload_image(image_body)
        model = await self.image_repository.create(
            user_id=schema.user_id,
            app_bundle=schema.app_bundle,
            prompt=schema.prompt,
            image_size=schema.image_size,
            resource_image_url=image_url
        )
        return ImageTaskSchema.model_validate(model)

    async def _send_image2image(self, schema: ImageTaskCreateSchema, image_url: str, image_id: UUID):
        request = AIInputSchema(
            prompt=schema.prompt,
            image_size=schema.image_size.value,
            seed=random.randint(0, 999999999)
        )

        logger.debug("Sending submit request to AI: " + str(request.model_dump()))
        try:
            response = await self.ai_repository.submit_img2img(request, image_url, str(image_id))
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

    async def store_ai_result(self, schema: AIOutputSchema, image_id: UUID):
        await self.image_repository.update(
            str(image_id),
            is_finished=True,
            image_url=schema.payload.images[0].url
        )

    async def get(self, image_id: UUID) -> ImageTaskSchema:
        model = await self.image_repository.get(str(image_id))
        return ImageTaskSchema.model_validate(model)

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
            if image.resource_image_url is not None:
                await self._send_image2image(schema, image.resource_image_url, image.id)
            else:
                await self._send(schema, image.id)

        try:
            await anext(session_getter)
        except StopAsyncIteration:
            pass

