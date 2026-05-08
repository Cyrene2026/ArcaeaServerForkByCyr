<<<<<<< HEAD
from fastapi import APIRouter, Depends
=======
from fastapi import APIRouter, Depends, Request
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979

from core.sql import Connect
from core.user import UserOnline, code_get_id

<<<<<<< HEAD
from .native import authed_user_id, game_success, is_error_response, server_try
from .schemas import FriendAddForm, FriendDeleteForm
=======
from .native import authed_user_id, form_data, game_success, is_error_response, server_try
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979

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
<<<<<<< HEAD
async def add_friend(payload: FriendAddForm = Depends(FriendAddForm.as_form), user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        friend_id = code_get_id(c, payload.friend_code)
=======
async def add_friend(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    form = await form_data(request)
    with Connect() as c:
        friend_code = form['friend_code']
        friend_id = code_get_id(c, friend_code)
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
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
<<<<<<< HEAD
async def delete_friend(payload: FriendDeleteForm = Depends(FriendDeleteForm.as_form), user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        friend_id = payload.friend_id
=======
async def delete_friend(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    form = await form_data(request)
    with Connect() as c:
        friend_id = int(form['friend_id'])
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
        user = UserOnline(c, user_id)
        user.delete_friend(friend_id)
        return game_success({
            "user_id": user.user_id,
            "updatedAt": "2020-09-07T07:32:12.740Z",
            "createdAt": "2020-09-06T10:05:18.471Z",
            "friends": user.friends
        })
