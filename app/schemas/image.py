from pydantic import BaseModel, HttpUrl, root_validator, ConfigDict, model_validator
from enum import Enum
from uuid import UUID
import datetime as dt


class ImageTaskSchema(BaseModel):
    id: UUID
    is_finished: bool
    is_invalid: bool = False
    image_url: HttpUrl | None = None
    comment: str | None = None

    @model_validator(mode='before')
    @classmethod
    def translate_status(cls, state):
        if not isinstance(state, dict):
            state = state.__dict__
        if state.get('status') and isinstance(state["status"], Enum):
            state["is_finished"] = state["status"].value == "finished"
            state["is_invalid"] = state["status"].value == "error"
        elif state.get('status') is None:
            state["is_finished"] = False
            state["is_invalid"] = False
        return state

    model_config = ConfigDict(from_attributes=True)


class ImageSize(Enum):
    square_hd = "square_hd"
    square = "square"
    portrait_4_3 = "portrait_4_3"
    portrait_16_9 = "portrait_16_9"
    landscape_4_3 = "landscape_4_3"
    landscape_16_9 = "landscape_16_9"


class ImageTaskCreateSchema(BaseModel):
    prompt: str
    image_size: ImageSize
    user_id: str
    app_bundle: str

    model_config = ConfigDict(from_attributes=True)

