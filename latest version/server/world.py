from fastapi import APIRouter, Depends, Request

from core.sql import Connect
from core.user import UserOnline
from core.world import MapParser, UserMap

from .native import authed_user_id, form_data, game_success, is_error_response, server_try

router = APIRouter(prefix='/world', tags=['game-world'])


@router.get('/map/me')
@server_try
def world_all(user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        user = UserOnline(c, user_id)
        user.select_user_about_current_map()
        return game_success({
            "current_map": user.current_map.map_id,
            "user_id": user_id,
            "maps": [x.to_dict(has_map_info=True, has_rewards=True) for x in MapParser.get_world_all(c, user)]
        })


@router.post('/map/me')
@server_try
async def world_in(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    form = await form_data(request)
    with Connect() as c:
        arcmap = UserMap(c, form['map_id'], UserOnline(c, user_id))
        if arcmap.unlock():
            return game_success(arcmap.to_dict())


@router.get('/map/me/{map_id}')
@server_try
def world_one(map_id: str, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        arcmap = UserMap(c, map_id, UserOnline(c, user_id))
        arcmap.change_user_current_map()
        return game_success({
            "user_id": user_id,
            "current_map": map_id,
            "maps": [arcmap.to_dict(has_map_info=True, has_steps=True)]
        })
