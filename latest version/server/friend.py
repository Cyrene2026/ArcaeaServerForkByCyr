from fastapi import APIRouter, Depends

from core.sql import Connect
from core.user import UserOnline, code_get_id

from .native import authed_user_id, game_success, is_error_response, server_try
from .schemas import FriendAddForm, FriendDeleteForm

router = APIRouter(prefix='/friend', tags=['game-friend'])


@router.get('/me')
@server_try
def friend_get(user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        user = UserOnline(c, user_id)
        return game_success({"friends": user.friends})


@router.post('/me/add')
@server_try
async def add_friend(payload: FriendAddForm = Depends(FriendAddForm.as_form), user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        friend_id = code_get_id(c, payload.friend_code)
        user = UserOnline(c, user_id)
        user.add_friend(friend_id)
        return game_success({
            "user_id": user.user_id,
            "updatedAt": "2020-09-07T07:32:12.740Z",
            "createdAt": "2020-09-06T10:05:18.471Z",
            "friends": user.friends
        })


@router.post('/me/delete')
@server_try
async def delete_friend(payload: FriendDeleteForm = Depends(FriendDeleteForm.as_form), user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        friend_id = payload.friend_id
        user = UserOnline(c, user_id)
        user.delete_friend(friend_id)
        return game_success({
            "user_id": user.user_id,
            "updatedAt": "2020-09-07T07:32:12.740Z",
            "createdAt": "2020-09-06T10:05:18.471Z",
            "friends": user.friends
        })
