from typing import Any, Optional

from pydantic import BaseModel, Field


class GameSuccessResponse(BaseModel):
    success: bool = Field(True, description='Whether the game API request succeeded.')
    value: Optional[Any] = Field(None, description='Game API response payload.')

    model_config = {
        'json_schema_extra': {
            'examples': [
                {'success': True, 'value': {'user_id': 2000000}},
            ],
        },
    }


class GameErrorResponse(BaseModel):
    success: bool = Field(False, description='Whether the game API request succeeded.')
    error_code: int = Field(..., description='Game protocol error code.')
    extra: Optional[Any] = Field(None, description='Optional extra error data.')

    model_config = {
        'json_schema_extra': {
            'examples': [
                {'success': False, 'error_code': 5},
            ],
        },
    }


class ApiSuccessResponse(BaseModel):
    code: int = Field(0, description='API status code. Zero means success.')
    data: Any = Field(default_factory=dict, description='API response payload.')
    msg: str = Field('', description='Human-readable message.')

    model_config = {
        'json_schema_extra': {
            'examples': [
                {'code': 0, 'data': {'user_id': 2000000}, 'msg': ''},
            ],
        },
    }


class ApiErrorResponse(BaseModel):
    code: int = Field(..., description='API error code. Negative values are API-layer errors.')
    data: Any = Field(default_factory=dict, description='Optional error payload.')
    msg: str = Field(..., description='Human-readable error message.')

    model_config = {
        'json_schema_extra': {
            'examples': [
                {'code': -1, 'data': {}, 'msg': 'No token'},
            ],
        },
    }


def to_jsonable(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True)
    return model.dict(exclude_none=True)
