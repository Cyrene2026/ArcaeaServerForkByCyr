import base64
import logging

<<<<<<< HEAD
from fastapi import APIRouter, Depends, Request
=======
from fastapi import APIRouter, Request
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979

from core.sql import Connect
from core.user import UserLogin

<<<<<<< HEAD
from .native import game_success, header_check, server_try
from .schemas import GameLoginForm
=======
from .native import form_data, game_success, header_check, server_try
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979

router = APIRouter(prefix='/auth', tags=['game-auth'])
logger = logging.getLogger('main')


@router.post('/login')
@server_try
<<<<<<< HEAD
async def login(request: Request, payload: GameLoginForm = Depends(GameLoginForm.as_form)):
=======
async def login(request: Request):
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
    headers = request.headers
    e = header_check(request)
    if e is not None:
        raise e

<<<<<<< HEAD
    payload.grant_type
=======
    form = await form_data(request)
    form['grant_type']
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
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
