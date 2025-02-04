from fastapi import APIRouter, Depends, Request, Header, HTTPException, Response
from fastapi import BackgroundTasks
from uuid import UUID
import os

from app.schemas.image import ImageTaskSchema, ImageTaskCreateSchema
from app.schemas.ai import AIOutputSchema
from app.services.image import ImageService

router = APIRouter(prefix="/image", tags=["Image"])
valid_access_token = os.getenv("ACCESS_TOKEN", "123")


@router.post(
    '',
    response_model=ImageTaskSchema,
    description="""
        Endpoint for start a task for image generation.
        For do request you need to specify Access-Token header, ask me in telegram about it.

        Image sizes: square_hd square portrait_4_3 portrait_16_9 landscape_4_3 landscape_16_9
    """
)
async def create_image_task(
        schema: ImageTaskCreateSchema,
        request: Request,
        background_tasks: BackgroundTasks,
        access_token: str = Header(),
        service: ImageService = Depends()
):
    if access_token != valid_access_token:
        raise HTTPException(401)
    image = await service.create(schema)
    background_tasks.add_task(service.send, schema, image.id)
    return image


@router.get(
    '/{image_id}',
    response_model=ImageTaskSchema,
    description="""
        Endpoint for check the task of image generation status.
        For do request you need to specify Access-Token header, ask me in telegram about it.
    """
)
async def get_image_task(
        image_id: UUID,
        request: Request,
        access_token: str = Header(),
        service: ImageService = Depends()
):
    if access_token != valid_access_token:
        raise HTTPException(401)
    return await service.get(image_id)


@router.post("/{image_id}/webhook", include_in_schema=False)
async def store_ai_result(
        image_id: UUID,
        schema: AIOutputSchema,
        service: ImageService = Depends()
):
    await service.store_ai_result(schema, image_id)
    return "OK"

