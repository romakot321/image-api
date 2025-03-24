import os
import io
import hashlib
import asyncio
import fal_client
from PIL import Image
from aiohttp import ClientSession, MultipartWriter, ClientTimeout
from pydantic import ValidationError
from loguru import logger
from uuid import uuid4

from app.schemas.ai import AIInputSchema, AIOutputSchema

token = os.getenv("API_TOKEN")


class AIRepository:
    API_WEBHOOK_BASEURL = os.getenv("API_WEBHOOK_BASEURL")

    async def submit(self, schema: AIInputSchema, image_id: str) -> str:
        """Return the request_id"""
        handler = await fal_client.submit_async(
            "fal-ai/flux/schnell",
            arguments=schema.model_dump(),
            webhook_url=(self.API_WEBHOOK_BASEURL + f"/image/{image_id}/webhook" if self.API_WEBHOOK_BASEURL is not None else None),
        )
        return handler.request_id

    async def is_finished(self, request_id: str) -> bool:
        status = await fal_client.status_async("fal-ai/flux/schnell", request_id, with_logs=True)
        logger.debug(status)
        return not isinstance(status, fal_client.InProgress)

    async def get_output(self, request_id: str) -> AIOutputSchema:
        result = await fal_client.result_async("fal-ai/flux/schnell", request_id)
        logger.debug(result)
        return AIOutputSchema.model_validate(result)

    async def upload_image(self, image_body: io.BytesIO) -> str:
        img = Image.open(image_body)
        return await fal_client.upload_image_async(img)

    async def submit_img2img(self, schema: AIInputSchema, image_url: str, image_id: str) -> str:
        """Return the request_id"""
        arguments = schema.model_dump()
        arguments["image_url"] = image_url
        handler = await fal_client.submit_async(
            "fal-ai/stable-diffusion-v3-medium/image-to-image",
            arguments=arguments,
            webhook_url=(self.API_WEBHOOK_BASEURL + f"/image/{image_id}/webhook" if self.API_WEBHOOK_BASEURL is not None else None),
        )
        return handler.request_id
