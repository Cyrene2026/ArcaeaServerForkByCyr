from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from core.api_user import APIUser
from core.error import DataExist, InputError, NoData
from core.item import Item, ItemFactory
from core.sql import Connect, Query, Sql

from .native import QueryPayload, api_success, require_api_user

router = APIRouter(prefix='/items', tags=['items'])

ALLOW_ITEM_TYPE = ['pack', 'single', 'world_song', 'character']


class ItemCreatePayload(BaseModel):
    item_id: Any
    type: Any
    is_available: Any = None

    model_config = ConfigDict(extra='ignore')


class ItemUpdatePayload(BaseModel):
    is_available: Any = None

    model_config = ConfigDict(extra='ignore')

    def to_data(self) -> dict:
        return self.model_dump(exclude_none=True)


@router.get('')
def items_get(
    data: QueryPayload = Depends(),
    user: APIUser = Depends(require_api_user(['select'])),
):
    '''查询全部物品信息'''
    with Connect() as c:
        query = Query(['item_id', 'type'], ['item_id'],
                      ['item_id']).from_dict(data.to_data())
        x = Sql(c).select('item', query=query)
        r: list[Item] = []
        for i in x:
            r.append(ItemFactory.from_dict({
                'item_id': i[0],
                'type': i[1],
                'is_available': i[2] == 1
            }))

        if not r:
            raise NoData(api_error_code=-2)

        return api_success([x.to_dict(has_is_available=True, has_amount=False) for x in r])


@router.post('')
def items_post(
    data: ItemCreatePayload,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''新增物品'''
    payload = data.model_dump(exclude_none=True)
    if payload['type'] not in ALLOW_ITEM_TYPE:
        raise InputError(
            f'Invalid item type: `{payload["type"]}`', api_error_code=-120)
    with Connect() as c:
        item = ItemFactory.from_dict(payload, c=c)
        if item.select_exists():
            raise DataExist(
                f'Item `{item.item_type}`: `{item.item_id}` already exists', api_error_code=-122)
        item.insert()
        return api_success(item.to_dict(has_is_available=True, has_amount=False))


@router.delete('/{item_type}/{item_id}')
def items_item_delete(
    item_type: str,
    item_id: str,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''删除物品'''
    if item_type not in ALLOW_ITEM_TYPE:
        raise InputError(
            f'Invalid item type: `{item_type}`', api_error_code=-120)
    with Connect() as c:
        item = ItemFactory.from_dict({
            'item_id': item_id,
            'type': item_type
        }, c=c)
        if not item.select_exists():
            raise NoData(
                f'No such item `{item_type}`: `{item_id}`', api_error_code=-121)
        item.delete()
        return api_success()


@router.put('/{item_type}/{item_id}')
def items_item_put(
    item_type: str,
    item_id: str,
    data: ItemUpdatePayload,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''修改物品'''
    payload = data.to_data()
    if not payload:
        raise InputError('No change', api_error_code=-100)
    if item_type not in ALLOW_ITEM_TYPE:
        raise InputError(
            f'Invalid item type: `{item_type}`', api_error_code=-120)
    if not isinstance(payload['is_available'], bool):
        raise InputError('`is_available` must be a boolean',
                         api_error_code=-101)
    with Connect() as c:
        item = ItemFactory.from_dict({
            'item_id': item_id,
            'type': item_type,
            'is_available': payload['is_available']
        }, c=c)
        if not item.select_exists():
            raise NoData(
                f'No such item `{item_type}`: `{item_id}`', api_error_code=-121)
        item.update()
        return api_success(item.to_dict(has_is_available=True, has_amount=False))


@router.get('/{item_type}/{item_id}')
def items_item_get(
    item_type: str,
    item_id: str,
    user: APIUser = Depends(require_api_user(['select'])),
):
    '''查询单个物品信息'''
    with Connect() as c:
        item = ItemFactory.from_dict({
            'item_id': item_id,
            'type': item_type
        }, c=c)
        item.select()
        return api_success(item.to_dict(has_is_available=True, has_amount=False))
