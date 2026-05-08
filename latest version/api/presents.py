from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from core.api_user import APIUser
from core.error import DataExist, InputError, NoData
from core.item import ItemFactory
from core.present import Present
from core.sql import Connect, Query, Sql

from .native import BatchPatchPayload, QueryPayload, api_success, require_api_user

router = APIRouter(prefix='/presents', tags=['presents'])


class PresentCreatePayload(BaseModel):
    present_id: Any
    description: Any
    expire_ts: Any
    items: Any = None

    model_config = ConfigDict(extra='ignore')


class PresentUpdatePayload(BaseModel):
    description: Any = None
    expire_ts: Any = None

    model_config = ConfigDict(extra='ignore')

    def to_data(self) -> dict:
        return {key: getattr(self, key) for key in self.model_fields_set}


@router.get('')
def presents_get(
    data: QueryPayload = Depends(),
    user: APIUser = Depends(require_api_user(['select'])),
):
    '''查询全部present信息'''
    with Connect() as c:
        query = Query(['present_id'], ['present_id', 'description'], [
                      'present_id', 'expire_ts']).from_dict(data.to_data())
        x = Sql(c).select('present', query=query)
        r = [Present().from_list(i) for i in x]

        if not r:
            raise NoData(api_error_code=-2)

        return api_success([x.to_dict(has_items=False) for x in r])


@router.post('')
def presents_post(
    data: PresentCreatePayload,
    user: APIUser = Depends(require_api_user(['insert'])),
):
    '''添加present，注意可以有items，不存在的item会自动创建'''
    payload = data.model_dump(exclude_none=True)
    with Connect() as c:
        p = Present(c).from_dict(payload)
        if p.select_exists():
            raise DataExist(
                f'Present `{p.present_id}` already exists')
        p.insert_all()
        return api_success(p.to_dict(has_items='items' in payload))


@router.get('/{present_id}')
def presents_present_get(
    present_id: str,
    user: APIUser = Depends(require_api_user(['select'])),
):
    '''查询单个present信息'''
    with Connect() as c:
        p = Present(c).select(present_id)
        p.select_items()
        return api_success(p.to_dict())


@router.delete('/{present_id}')
def presents_present_delete(
    present_id: str,
    user: APIUser = Depends(require_api_user(['delete'])),
):
    '''删除present，会连带删除present_item'''
    with Connect() as c:
        Present(c).select(present_id).delete_all()
        return api_success()


@router.put('/{present_id}')
def presents_present_put(
    present_id: str,
    data: PresentUpdatePayload,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''更新present信息，注意不能有items'''
    payload = data.to_data()
    if not payload:
        raise InputError('No change', api_error_code=-100)
    with Connect() as c:
        p = Present(c).select(present_id)
        if 'description' in payload:
            p.description = str(payload['description'])
        if 'expire_ts' in payload:
            p.expire_ts = int(payload['expire_ts'])
        p.update()
        return api_success(p.to_dict(has_items=False))


@router.get('/{present_id}/items')
def presents_present_items_get(
    present_id: str,
    user: APIUser = Depends(require_api_user(['select'])),
):
    '''查询present的items'''
    with Connect() as c:
        p = Present(c)
        p.present_id = present_id
        p.select_items()
        return api_success([x.to_dict(has_is_available=True) for x in p.items])


@router.patch('/{present_id}/items')
def presents_present_items_patch(
    present_id: str,
    data: BatchPatchPayload,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''增删改单个present的items'''
    payload = data.to_data()
    if not payload:
        raise InputError('No change', api_error_code=-100)
    with Connect() as c:
        p = Present(c)
        p.present_id = present_id
        p.select_items()
        p.remove_items([ItemFactory.from_dict(x, c=c)
                        for x in payload.get('remove', [])])
        p.add_items([ItemFactory.from_dict(x, c=c)
                     for x in payload.get('create', [])])

        updates = payload.get('update', [])
        for x in updates:
            if 'amount' not in x:
                raise InputError('`amount` is required in `update`')
            if not isinstance(x['amount'], int) or x['amount'] <= 0:
                raise InputError(
                    '`amount` must be a positive integer', api_error_code=-101)

        p.update_items([ItemFactory.from_dict(x, c=c) for x in updates])
        return api_success([x.to_dict(has_is_available=True) for x in p.items])
