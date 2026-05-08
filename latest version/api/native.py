from __future__ import annotations

from typing import Any, Callable

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.status import HTTP_400_BAD_REQUEST

from core.api_user import APIUser
from core.config_manager import Config
from core.error import ArcError, InputError, NoAccess, PostError
from core.sql import Connect

from .api_code import CODE_MSG


class ApiResponseException(Exception):
    def __init__(self, response: JSONResponse) -> None:
        self.response = response


class QueryPayload(BaseModel):
    limit: Any = None
    offset: Any = None
    query: Any = None
    fuzzy_query: Any = None
    sort: Any = None

    model_config = ConfigDict(extra='ignore')

    def to_data(self) -> dict:
        return self.model_dump(exclude_none=True)


class BatchPatchPayload(BaseModel):
    create: list[Any] | None = None
    update: list[Any] | None = None
    remove: list[Any] | None = None

    model_config = ConfigDict(extra='ignore')

    def to_data(self) -> dict:
        return self.model_dump(exclude_none=True)


def api_success(data: Any = None, status: int = 200, msg: str = '') -> JSONResponse:
    if data is None:
        data = {}
    return JSONResponse({'code': 0, 'data': data, 'msg': msg}, status_code=status)


def api_error(e: ArcError, status: int | None = None) -> JSONResponse:
    return JSONResponse({
        'code': e.api_error_code,
        'data': {} if e.extra_data is None else e.extra_data,
        'msg': CODE_MSG[e.api_error_code] if e.message is None else e.message,
    }, status_code=status if status is not None else e.status)


def require_api_user(powers: list[str]) -> Callable:
    def dependency(token: str | None = Header(default=None, alias='Token')) -> APIUser:
        if token is None:
            raise ApiResponseException(
                api_error(PostError('No token', api_error_code=-1), 401))

        user = APIUser()
        with Connect() as c:
            user.c = c
            if Config.API_TOKEN == token and Config.API_TOKEN != '':
                user.set_role_system()
                return user
            try:
                user.select_user_id_from_api_token(token)
                user.select_role_and_powers()
                if not any(user.role.has_power(power) for power in powers):
                    raise ApiResponseException(
                        api_error(NoAccess('No permission', api_error_code=-1), 403))
                return user
            except ApiResponseException:
                raise
            except ArcError as e:
                raise ApiResponseException(api_error(e, 401)) from e

    return dependency


def require_self_or_power(user: APIUser, user_id: int, power: str = 'select') -> JSONResponse | None:
    if user_id <= 0:
        return api_error(InputError(api_error_code=-110))
    if user_id != user.user_id and not user.role.has_power(power):
        return api_error(NoAccess('No permission', api_error_code=-1), 403)
    return None


async def api_response_exception_handler(request: Request, exc: ApiResponseException):
    return exc.response


async def arc_error_exception_handler(request: Request, exc: ArcError):
    return api_error(exc, exc.status)


async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0] if exc.errors() else {}
    if first_error.get('type') == 'json_invalid':
        return api_error(
            PostError('Payload must be a valid json', api_error_code=-1),
            HTTP_400_BAD_REQUEST,
        )

    loc = [part for part in first_error.get('loc', []) if part != 'body']
    field = '.'.join(map(str, loc)) if loc else 'payload'
    if first_error.get('type') == 'list_type':
        return api_error(InputError(f'Parameter {field} must be a list', api_error_code=-100))
    return api_error(InputError(f'Missing parameter: {field}', api_error_code=-100))


def install_native_api_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiResponseException, api_response_exception_handler)
    app.add_exception_handler(ArcError, arc_error_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
