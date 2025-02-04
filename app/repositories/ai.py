import os
import hashlib
import asyncio
import fal_client
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

