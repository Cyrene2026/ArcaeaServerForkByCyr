from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from core.api_user import APIUser
from core.config_manager import Config
from core.error import InputError, NoAccess, NoData
from core.score import Potential, UserScoreList
from core.sql import Connect, Query, Sql
from core.user import UserChanger, UserInfo, UserRegister
from core.util import get_today_timestamp

from .native import QueryPayload, api_error, api_success, require_api_user, require_self_or_power

router = APIRouter(prefix='/users', tags=['users'])


class UserCreatePayload(BaseModel):
    name: Any
    password: Any
    email: Any

    model_config = ConfigDict(extra='ignore')


class UserUpdatePayload(BaseModel):
    name: Any = None
    password: Any = None
    user_code: Any = None
    ticket: Any = None
    email: Any = None
    custom_banner: Any = None

    model_config = ConfigDict(extra='ignore')

    def to_data(self) -> dict:
        return {
            key: getattr(self, key)
            for key in self.model_fields_set
        }


class UserRatingQuery(BaseModel):
    start_timestamp: Any = None
    end_timestamp: Any = None
    duration: Any = None

    model_config = ConfigDict(extra='ignore')

    def to_data(self) -> dict:
        return self.model_dump(exclude_none=True)


@router.post('')
def users_post(
    data: UserCreatePayload,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''注册一个用户'''
    payload = data.model_dump()
    with Connect() as c:
        new_user = UserRegister(c)
        new_user.set_name(payload['name'])
        new_user.set_password(payload['password'])
        new_user.set_email(payload['email'])
        new_user.register()
        return api_success({'user_id': new_user.user_id, 'user_code': new_user.user_code})


@router.get('')
def users_get(
    data: QueryPayload = Depends(),
    user: APIUser = Depends(require_api_user(['select'])),
):
    '''查询全部用户信息'''
    a = ['user_id', 'name', 'user_code']
    b = ['user_id', 'name', 'user_code', 'join_date',
         'rating_ptt', 'time_played', 'ticket', 'world_rank_score']
    with Connect() as c:
        query = Query(a, a, b).from_dict(data.to_data())
        x = Sql(c).select('user', query=query)
        r = []
        for i in x:
            r.append(UserInfo(c).from_list(i))

        if not r:
            raise NoData(api_error_code=-2)

        return api_success([{
            'user_id': x.user_id,
            'name': x.name,
            'join_date': x.join_date,
            'user_code': x.user_code,
            'rating_ptt': x.rating_ptt,
            'character_id': x.character.character_id,
            'is_char_uncapped': x.character.is_uncapped,
            'is_char_uncapped_override': x.character.is_uncapped_override,
            'is_hide_rating': x.is_hide_rating,
            'ticket': x.ticket
        } for x in r])


@router.get('/{user_id}')
def users_user_get(
    user_id: int,
    user: APIUser = Depends(require_api_user(['select', 'select_me'])),
):
    '''查询用户信息'''
    error = require_self_or_power(user, user_id, 'select')
    if error is not None:
        return error

    with Connect() as c:
        u = UserInfo(c, user_id)
        return api_success(u.to_dict())


@router.put('/{user_id}')
def users_user_put(
    user_id: int,
    data: UserUpdatePayload,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''修改一个用户'''
    payload = data.to_data()
    if not payload:
        raise InputError('No change', api_error_code=-100)

    with Connect() as c:
        u = UserChanger(c, user_id)
        r = {'user_id': user_id}
        if 'name' in payload:
            u.set_name(payload['name'])
            r['name'] = u.name
        if 'password' in payload:
            if payload['password'] == '':
                u.password = ''
                r['password'] = ''
            else:
                u.set_password(payload['password'])
                r['password'] = u.hash_pwd
        if 'email' in payload:
            u.set_email(payload['email'])
            r['email'] = u.email
        if 'user_code' in payload:
            u.set_user_code(payload['user_code'])
            r['user_code'] = u.user_code
        if 'ticket' in payload:
            if not isinstance(payload['ticket'], int):
                raise InputError('Ticket must be int')
            u.ticket = payload['ticket']
            r['ticket'] = u.ticket
        if 'custom_banner' in payload:
            if not isinstance(payload['custom_banner'], str):
                raise InputError('Value `custom_banner` must be str')
            u.custom_banner = payload['custom_banner']
            r['custom_banner'] = u.custom_banner
        u.update_columns(d=r)
        return api_success(r)


@router.get('/{user_id}/b30')
def users_user_b30_get(
    user_id: int,
    user: APIUser = Depends(require_api_user(['select', 'select_me'])),
):
    '''查询用户b30'''
    error = require_self_or_power(user, user_id, 'select')
    if error is not None:
        return error

    with Connect() as c:
        x = UserScoreList(c, UserInfo(c, user_id))
        x.query.limit = 30
        x.select_from_user()
        if not x.scores:
            raise NoData(
                f'No best30 data of user `{user_id}`', api_error_code=-3)
        x.select_song_name()
        r = x.to_dict_list()
        rating_sum = sum(i.rating for i in x.scores)
        return api_success({'user_id': user_id, 'b30_ptt': rating_sum / 30, 'data': r})


@router.get('/{user_id}/best')
def users_user_best_get(
    user_id: int,
    data: QueryPayload = Depends(),
    user: APIUser = Depends(require_api_user(['select', 'select_me'])),
):
    '''查询用户所有best成绩'''
    error = require_self_or_power(user, user_id, 'select')
    if error is not None:
        return error

    with Connect() as c:
        x = UserScoreList(c, UserInfo(c, user_id))
        x.query.from_dict(data.to_data())
        x.select_from_user()
        if not x.scores:
            raise NoData(
                f'No best score data of user `{user_id}`', api_error_code=-3)
        r = x.to_dict_list()
        return api_success({'user_id': user_id, 'data': r})


@router.get('/{user_id}/r30')
def users_user_r30_get(
    user_id: int,
    user: APIUser = Depends(require_api_user(['select', 'select_me'])),
):
    '''查询用户r30'''
    error = require_self_or_power(user, user_id, 'select')
    if error is not None:
        return error

    with Connect() as c:
        p = Potential(c, UserInfo(c, user_id))
        return api_success({'user_id': user_id, 'r10_ptt': p.recent_10 / 10, 'data': p.recent_30_to_dict_list()})


@router.get('/{user_id}/role')
def users_user_role_get(
    user_id: int,
    user: APIUser = Depends(require_api_user(['select', 'select_me'])),
):
    '''查询用户role和powers'''
    if user_id <= 0:
        return api_error(InputError(api_error_code=-110))

    if user_id == user.user_id:
        return api_success({'user_id': user.user_id, 'role': user.role.role_id, 'powers': [i.power_id for i in user.role.powers]})
    if not user.role.has_power('select'):
        return api_error(NoAccess('No permission', api_error_code=-1), 403)

    with Connect() as c:
        x = APIUser(c, user_id)
        x.select_role_and_powers()
        return api_success({'user_id': x.user_id, 'role': x.role.role_id, 'powers': [i.power_id for i in x.role.powers]})


@router.get('/{user_id}/rating')
def users_user_rating_get(
    user_id: int,
    data: UserRatingQuery = Depends(),
    user: APIUser = Depends(require_api_user(['select', 'select_me'])),
):
    '''查询用户历史rating，duration是相对于今天的天数'''
    if user_id != user.user_id and not user.role.has_power('select'):
        return api_error(NoAccess('No permission', api_error_code=-1), 403)

    payload = data.to_data()
    start_timestamp = payload.get('start_timestamp', None)
    end_timestamp = payload.get('end_timestamp', None)
    duration = payload.get('duration', None)
    sql = '''select time, rating_ptt from user_rating where user_id = ?'''
    sql_data = [user_id]
    if start_timestamp is not None and end_timestamp is not None:
        sql += ''' and time between ? and ?'''
        sql_data += [start_timestamp, end_timestamp]
    elif duration is not None:
        sql += ''' and time between ? and ?'''
        t = get_today_timestamp()
        sql_data += [t - duration * 24 * 3600, t]

    with Connect(Config.SQLITE_LOG_DATABASE_PATH) as c:
        c.execute(sql, sql_data)
        r = c.fetchall()
        return api_success({'user_id': user_id, 'data': [{'time': i[0], 'rating_ptt': i[1]} for i in r]})
