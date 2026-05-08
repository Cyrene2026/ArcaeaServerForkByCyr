from fastapi import APIRouter, Depends

from core.present import UserPresent, UserPresentList
from core.sql import Connect
from core.user import UserOnline

from .native import authed_user_id, game_success, is_error_response, server_try

router = APIRouter(prefix='/present', tags=['game-present'])


@router.get('/me')
@server_try
def present_info(user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        x = UserPresentList(c, UserOnline(c, user_id))
        x.select_user_presents()
        return game_success(x.to_dict_list())


@router.post('/me/claim/{present_id}')
@server_try
def claim_present(present_id: str, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        x = UserPresent(c, UserOnline(c, user_id))
        x.claim_user_present(present_id)
        return game_success()
