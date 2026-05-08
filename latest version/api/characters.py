from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from core.api_user import APIUser
from core.character import Character
from core.error import InputError, NoData
from core.item import ItemFactory
from core.sql import Connect, Query, Sql

from .constant import Constant
from .native import BatchPatchPayload, QueryPayload, api_success, require_api_user

router = APIRouter(prefix='/characters', tags=['characters'])


class CharacterUpdatePayload(BaseModel):
    max_level: Any = None
    skill_id: Any = None
    skill_id_uncap: Any = None
    skill_unlock_level: Any = None
    skill_requires_uncap: Any = None
    char_type: Any = None
    is_uncapped: Any = None
    frag1: Any = None
    prog1: Any = None
    overdrive1: Any = None
    frag20: Any = None
    prog20: Any = None
    overdrive20: Any = None
    frag30: Any = None
    prog30: Any = None
    overdrive30: Any = None

    model_config = ConfigDict(extra='ignore')

    def to_data(self) -> dict:
        return {key: getattr(self, key) for key in self.model_fields_set}


@router.get('')
def characters_get(
    data: QueryPayload = Depends(),
    user: APIUser = Depends(require_api_user(['select'])),
):
    '''查询全部角色信息'''
    a = ['character_id', 'name', 'skill_id',
         'skill_id_uncap', 'char_type', 'is_uncapped']
    b = ['name', 'skill_id', 'skill_id_uncap']
    c_cols = ['name', 'frag1', 'prog1', 'overdrive1', 'frag20',
              'prog20', 'overdrive20', 'frag30', 'prog30', 'overdrive30']
    with Connect() as c:
        query = Query(a, b, c_cols).from_dict(data.to_data())
        x = Sql(c).select('character', query=query)
        r = [Character().from_list(i) for i in x]

        if not r:
            raise NoData(api_error_code=-2)

        return api_success([x.to_dict() for x in r])


@router.get('/{character_id}')
def characters_character_get(
    character_id: int,
    user: APIUser = Depends(require_api_user(['select'])),
):
    with Connect() as c:
        character = Character(c).select(character_id)
        character.select_character_core()
        return api_success(character.to_dict(has_cores=True))


@router.put('/{character_id}')
def characters_character_put(
    character_id: int,
    data: CharacterUpdatePayload,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''修改角色信息'''
    payload = data.to_data()
    if not payload:
        raise InputError('No change', api_error_code=-100)
    if ('skill_id' in payload and payload['skill_id'] != '' and payload['skill_id'] not in Constant.SKILL_IDS) or ('skill_id_uncap' in payload and payload['skill_id_uncap'] != '' and payload['skill_id_uncap'] not in Constant.SKILL_IDS):
        raise InputError('Invalid skill_id', api_error_code=-131)
    with Connect() as c:
        character = Character(c).select(character_id)
        try:
            if 'max_level' in payload:
                character.max_level = int(payload['max_level'])
            if 'skill_id' in payload:
                character.skill_id = payload['skill_id']
            if 'skill_id_uncap' in payload:
                character.skill_id_uncap = payload['skill_id_uncap']
            if 'skill_unlock_level' in payload:
                character.skill_unlock_level = int(payload['skill_unlock_level'])
            if 'skill_requires_uncap' in payload:
                character.skill_requires_uncap = payload['skill_requires_uncap'] == 1
            if 'char_type' in payload:
                character.char_type = int(payload['char_type'])
            if 'is_uncapped' in payload:
                character.is_uncapped = payload['is_uncapped'] == 1
            t = ['frag1', 'prog1', 'overdrive1', 'frag20', 'prog20',
                 'overdrive20', 'frag30', 'prog30', 'overdrive30']
            for i in t:
                if i not in payload:
                    continue
                if i.endswith('1'):
                    x = getattr(character, i[:-1])
                    x.start = float(payload[i])
                elif i.endswith('20'):
                    x = getattr(character, i[:-2])
                    x.mid = float(payload[i])
                else:
                    x = getattr(character, i[:-2])
                    x.end = float(payload[i])
        except ValueError as e:
            raise InputError('Invalid input', api_error_code=-101) from e
        character.update()
        return api_success(character.to_dict())


@router.get('/{character_id}/cores')
def characters_character_cores_get(
    character_id: int,
    user: APIUser = Depends(require_api_user(['select'])),
):
    with Connect() as c:
        character = Character(c)
        character.character_id = character_id
        character.select_character_core()
        return api_success(character.uncap_cores_to_dict())


@router.patch('/{character_id}/cores')
def characters_character_cores_patch(
    character_id: int,
    data: BatchPatchPayload,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''修改角色觉醒cores'''

    def force_type_core(x: dict) -> dict:
        x['item_type'] = 'core'
        x['type'] = 'core'
        return x

    payload = data.to_data()
    if not payload:
        raise InputError('No change', api_error_code=-100)

    with Connect() as c:
        ch = Character(c)
        ch.character_id = character_id
        ch.select_character_core()
        ch.remove_items([ItemFactory.from_dict(x, c=c)
                         for x in map(force_type_core, payload.get('remove', []))])
        ch.add_items([ItemFactory.from_dict(x, c=c)
                      for x in map(force_type_core, payload.get('create', []))])
        updates = list(map(force_type_core, payload.get('update', [])))
        for x in updates:
            if 'amount' not in x:
                raise InputError('`amount` is required in `update`')
            if not isinstance(x['amount'], int) or x['amount'] <= 0:
                raise InputError(
                    '`amount` must be a positive integer', api_error_code=-101)

        ch.update_items(
            [ItemFactory.from_dict(x, c=c) for x in updates])
        return api_success(ch.uncap_cores_to_dict())
