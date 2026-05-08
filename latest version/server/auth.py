import base64
import logging

from fastapi import APIRouter, Request

from core.sql import Connect
from core.user import UserLogin

from .native import form_data, game_success, header_check, server_try

router = APIRouter(prefix='/auth', tags=['game-auth'])
logger = logging.getLogger('main')


@router.post('/login')
@server_try
async def login(request: Request):
    headers = request.headers
    e = header_check(request)
    if e is not None:
        raise e

    form = await form_data(request)
    form['grant_type']
    with Connect() as c:
        id_pwd = headers['Authorization']
        id_pwd = base64.b64decode(id_pwd[6:]).decode()
        name, password = id_pwd.split(':', 1)
        if 'DeviceId' in headers:
            device_id = headers['DeviceId']
        else:
            device_id = 'low_version'

        user = UserLogin(c)
        ip = request.client.host if request.client else ''
        user.login(name, password, device_id, ip)
        logger.info(f'User `{user.user_id}` log in')
        return game_success({"token_type": "Bearer", 'user_id': user.user_id, 'access_token': user.token})
