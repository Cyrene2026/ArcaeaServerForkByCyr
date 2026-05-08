from __future__ import annotations

import inspect
import logging
from functools import wraps
from traceback import format_exc
from typing import Any, Callable

from fastapi import Depends, Request
from fastapi.responses import JSONResponse

from core.bundle import BundleParser
from core.config_manager import Config
from core.error import ArcError, LowVersion, NoAccess
from core.response_models import GameErrorResponse, GameSuccessResponse, to_jsonable
from core.sql import Connect
from core.user import UserAuth

has_arc_hash = False
try:
    from core.arc_crypto import ArcHashChecker  # type: ignore
    has_arc_hash = True
except ModuleNotFoundError:
    pass

logger = logging.getLogger('main')
default_error = ArcError('Unknown Error', status=500)


def game_error(e: ArcError = default_error) -> JSONResponse:
    return JSONResponse(
        to_jsonable(GameErrorResponse(error_code=e.error_code, extra=e.extra_data)),
        status_code=e.status,
    )


def game_success(value: Any = None) -> JSONResponse:
    return JSONResponse(to_jsonable(GameSuccessResponse(value=value)))


def server_try(view: Callable) -> Callable:
    @wraps(view)
    async def wrapped_view(*args, **kwargs):
        try:
            data = view(*args, **kwargs)
            if inspect.isawaitable(data):
                data = await data
            if data is None:
                return game_error()
            return data
        except ArcError as e:
            if Config.ALLOW_WARNING_LOG:
                logger.warning(format_exc())
            request = kwargs.get('request')
            user = getattr(getattr(request, 'state', None), 'user', None)
            logger.warning(
                f'{user.user_id if user is not None else ""} - {e.error_code}|{e.api_error_code}: {e}')
            return game_error(e)

    return wrapped_view


def header_check(request: Request) -> ArcError | None:
    headers = request.headers
    if Config.ALLOW_APPVERSION:
        if 'AppVersion' not in headers or headers['AppVersion'] not in Config.ALLOW_APPVERSION:
            return LowVersion('Invalid app version', 5)
    if request.method == 'GET' and 'ContentBundle' in headers and headers['ContentBundle'] != BundleParser.max_bundle_version.get(headers.get('AppVersion', ''), '0.0.0'):
        return LowVersion('Invalid content bundle version', 11)

    if has_arc_hash and not ArcHashChecker(request).check():
        return NoAccess('Invalid request')

    return None


def require_game_user(request: Request) -> int | JSONResponse:
    e = header_check(request)
    if e is not None:
        logger.warning(f' - {e.error_code}|{e.api_error_code}: {e}')
        return game_error(e)

    with Connect() as c:
        try:
            user = UserAuth(c)
            token = request.headers.get('Authorization')
            if not token:
                raise NoAccess('No token.', -4)
            user.token = token[7:]
            user_id = user.token_get_id()
            request.state.user = user
            return user_id
        except ArcError as e:
            return game_error(e)


def authed_user_id(user_id: int | JSONResponse = Depends(require_game_user)) -> int | JSONResponse:
    return user_id


def is_error_response(value: Any) -> bool:
    return isinstance(value, JSONResponse)


async def form_data(request: Request):
    return await request.form()


def form_get(form, key: str, default: Any = None, type: Callable | None = None) -> Any:
    value = form.get(key, default)
    if value is default or type is None:
        return value
    try:
        return type(value)
    except (TypeError, ValueError):
        return default


def query_get(request: Request, key: str, default: Any = None, type: Callable | None = None) -> Any:
    value = request.query_params.get(key, default)
    if value is default or type is None:
        return value
    try:
        return type(value)
    except (TypeError, ValueError):
        return default


def string_to_list(value):
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return []
    return value
