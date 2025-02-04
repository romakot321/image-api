from pydantic import BaseModel, ConfigDict
from uuid import UUID
from enum import Enum


class AIOutputSchema(BaseModel):
    class OutputPayload(BaseModel):
        class AIImageSchema(BaseModel):
            url: str
            content_type: str = "image/jpeg"
            width: int
            height: int

        images: list[AIImageSchema]
        seed: int

    payload: OutputPayload
    status: str
    request_id: str

    model_config = ConfigDict(from_attributes=True)


class AIInputSchema(BaseModel):
    prompt: str
    image_size: str
    seed: int
