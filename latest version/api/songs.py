from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from core.api_user import APIUser
from core.error import DataExist, InputError, NoData
from core.rank import RankList
from core.song import Song
from core.sql import Connect, Query, Sql

from .native import QueryPayload, api_success, require_api_user

router = APIRouter(prefix='/songs', tags=['songs'])


class SongCreatePayload(BaseModel):
    song_id: Any
    charts: Any
    name: Any = None

    model_config = ConfigDict(extra='ignore')


class SongUpdatePayload(BaseModel):
    name: Any = None
    charts: Any = None

    model_config = ConfigDict(extra='ignore')

    def to_data(self) -> dict:
        return {key: getattr(self, key) for key in self.model_fields_set}


class SongRankQuery(BaseModel):
    limit: Any = None

    model_config = ConfigDict(extra='ignore')

    def to_data(self) -> dict:
        return self.model_dump(exclude_none=True)


@router.get('/{song_id}')
def songs_song_get(
    song_id: str,
    user: APIUser = Depends(require_api_user(['select', 'select_song_info'])),
):
    '''查询歌曲信息'''
    with Connect() as c:
        s = Song(c, song_id).select()
        return api_success(s.to_dict())


@router.put('/{song_id}')
def songs_song_put(
    song_id: str,
    data: SongUpdatePayload,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''修改歌曲信息'''
    payload = data.to_data()
    if not payload:
        raise InputError('No change', api_error_code=-100)
    with Connect() as c:
        s = Song(c, song_id).select()
        if 'name' in payload:
            s.name = str(payload['name'])
        if 'charts' in payload:
            for i in payload['charts']:
                if 'difficulty' in i and 'chart_const' in i:
                    s.charts[i['difficulty']].defnum = round(
                        i['chart_const'] * 10)

        s.update()
        return api_success(s.to_dict())


@router.delete('/{song_id}')
def songs_song_delete(
    song_id: str,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''删除歌曲信息'''
    with Connect() as c:
        s = Song(c, song_id)
        if not s.select_exists():
            raise NoData(f'No such song: `{song_id}`')
        s.delete()
        return api_success()


@router.get('')
def songs_get(
    data: QueryPayload = Depends(),
    user: APIUser = Depends(require_api_user(['select', 'select_song_info'])),
):
    '''查询全部歌曲信息'''
    a = ['song_id', 'name']
    b = ['song_id', 'name', 'rating_pst',
         'rating_prs', 'rating_ftr', 'rating_byn', 'rating_etr']
    with Connect() as c:
        query = Query(a, a, b).from_dict(data.to_data())
        x = Sql(c).select('chart', query=query)
        r = []
        for i in x:
            r.append(Song(c).from_list(i))

        if not r:
            raise NoData(api_error_code=-2)

        return api_success([x.to_dict() for x in r])


@router.post('')
def songs_post(
    data: SongCreatePayload,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''添加歌曲信息'''
    payload = data.model_dump(exclude_none=True)
    with Connect() as c:
        s = Song(c).from_dict(payload)
        if s.select_exists():
            raise DataExist(f'Song `{s.song_id}` already exists')
        s.insert()
        return api_success(s.to_dict())


@router.get('/{song_id}/{difficulty}/rank')
def songs_song_difficulty_rank_get(
    song_id: str,
    difficulty: int,
    data: SongRankQuery = Depends(),
    user: APIUser = Depends(require_api_user(['select', 'select_song_rank', 'select_song_rank_top'])),
):
    '''查询歌曲某个难度的成绩排行榜，和游戏内接口相似，只允许limit'''
    if difficulty not in [0, 1, 2, 3, 4]:
        raise InputError('Difficulty must be 0, 1, 2, 3 or 4')
    payload = data.to_data()
    limit = payload.get('limit', 20)
    if not isinstance(limit, int):
        raise InputError('Limit must be int')
    if user.role.only_has_powers(['select_song_rank_top'], ['select', 'select_song_rank']):
        if limit > 20 or limit < 0:
            limit = 20
    with Connect() as c:
        rank_list = RankList(c)
        rank_list.song.set_chart(song_id, difficulty)
        rank_list.limit = limit
        rank_list.select_top()
        return api_success(rank_list.to_dict_list())
