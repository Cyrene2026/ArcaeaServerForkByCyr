from typing import Any, Optional

from pydantic import BaseModel, Field


class GameSuccessResponse(BaseModel):
    success: bool = True
    value: Optional[Any] = None


class GameErrorResponse(BaseModel):
    success: bool = False
    error_code: int
    extra: Optional[Any] = None


class ApiSuccessResponse(BaseModel):
    code: int = 0
    data: dict[str, Any] = Field(default_factory=dict)
    msg: str = ""


class ApiErrorResponse(BaseModel):
    code: int
    data: Any = Field(default_factory=dict)
    msg: str


def to_jsonable(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True)
    return model.dict(exclude_none=True)
