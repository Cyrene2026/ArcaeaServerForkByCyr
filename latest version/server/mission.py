from fastapi import APIRouter, Depends, Request

from core.error import NoData
from core.mission import MISSION_DICT
from core.sql import Connect
from core.user import UserOnline

from .native import authed_user_id, form_data, game_success, is_error_response, server_try

router = APIRouter(prefix='/mission', tags=['game-mission'])


def parse_mission_form(multidict) -> list:
    r = []
    x = multidict.get('mission_1')
    i = 1
    while x:
        r.append(x)
        x = multidict.get(f'mission_{i + 1}')
        i += 1
    return r


@router.post('/me/clear')
@server_try
async def mission_clear(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    form = await form_data(request)
    m = parse_mission_form(form)
    r = []
    for i, mission_id in enumerate(m):
        if mission_id not in MISSION_DICT:
            raise NoData(f'Mission `{mission_id}` not found')
        with Connect() as c:
            x = MISSION_DICT[mission_id](c)
            x.user_clear_mission(UserOnline(c, user_id))
            d = x.to_dict()
            d['request_id'] = i + 1
            r.append(d)
    return game_success({'missions': r})


@router.post('/me/claim')
@server_try
async def mission_claim(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    form = await form_data(request)
    m = parse_mission_form(form)
    r = []
    with Connect() as c:
        user = UserOnline(c, user_id)
        for i, mission_id in enumerate(m):
            if mission_id not in MISSION_DICT:
                raise NoData(f'Mission `{mission_id}` not found')
            x = MISSION_DICT[mission_id](c)
            x.user_claim_mission(user)
            d = x.to_dict(has_items=True)
            d['request_id'] = i + 1
            r.append(d)
        return game_success({
            'missions': r,
            'user': user.to_dict()
        })
