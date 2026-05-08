from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from core.api_user import APIUser
from core.linkplay import RemoteMultiPlayer

from .native import api_success, require_api_user

router = APIRouter(prefix='/multiplay', tags=['multiplay'])


class RoomsQuery(BaseModel):
    offset: Any = 0
    limit: Any = 100

    model_config = ConfigDict(extra='ignore')


@router.get('/rooms')
def rooms_get(
    data: RoomsQuery = Depends(),
    user: APIUser = Depends(require_api_user(['select'])),
):
    '''获取房间列表'''
    r = RemoteMultiPlayer().get_rooms(offset=data.offset, limit=data.limit)
    return api_success(r)
