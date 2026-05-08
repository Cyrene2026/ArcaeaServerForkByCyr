from base64 import b64decode
import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from core.api_user import APIUser
from core.error import PostError
from core.sql import Connect

from .native import api_success, require_api_user

router = APIRouter(prefix='/token', tags=['token'])
logger = logging.getLogger('main')


class TokenLoginPayload(BaseModel):
    auth: str

    model_config = ConfigDict(extra='ignore')


@router.post('')
def token_post(payload: TokenLoginPayload, request: Request):
    '''
        登录，获取token

        {'auth': base64('<user_id>:<password>')}
    '''
    try:
        auth_decode = bytes.decode(b64decode(payload.auth))
    except Exception as e:
        raise PostError(api_error_code=-100) from e
    if ':' not in auth_decode:
        raise PostError(api_error_code=-100)
    name, password = auth_decode.split(':', 1)

    with Connect() as c:
        user = APIUser(c)
        ip = request.client.host if request.client else None
        user.login(name, password, ip)
        logger.info(f'API user `{user.user_id}` log in')
        return api_success({'token': user.api_token, 'user_id': user.user_id})


@router.get('')
def token_get(user: APIUser = Depends(require_api_user(['select_me', 'select']))):
    '''判断登录有效性'''
    return api_success()


@router.delete('')
def token_delete(user: APIUser = Depends(require_api_user(['change_me', 'select_me', 'select']))):
    '''登出'''
    with Connect() as c:
        user.c = c
        user.logout()
        return api_success()
