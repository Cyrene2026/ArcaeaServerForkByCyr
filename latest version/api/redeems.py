from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from core.api_user import APIUser
from core.error import DataExist, InputError, NoData
from core.item import ItemFactory
from core.redeem import Redeem
from core.sql import Connect, Query, Sql

from .native import BatchPatchPayload, QueryPayload, api_success, require_api_user

router = APIRouter(prefix='/redeems', tags=['redeems'])


class RedeemCreatePayload(BaseModel):
    code: Any
    type: Any
    items: Any = None

    model_config = ConfigDict(extra='ignore')


class RedeemUpdatePayload(BaseModel):
    type: Any = None

    model_config = ConfigDict(extra='ignore')

    def to_data(self) -> dict:
        return {key: getattr(self, key) for key in self.model_fields_set}


@router.get('')
def redeems_get(
    data: QueryPayload = Depends(),
    user: APIUser = Depends(require_api_user(['select'])),
):
    '''查询全部redeem信息'''
    with Connect() as c:
        query = Query(['code', 'type'], ['code'], ['code']).from_dict(data.to_data())
        x = Sql(c).select('redeem', query=query)
        r = [Redeem().from_list(i) for i in x]

        if not r:
            raise NoData(api_error_code=-2)

        return api_success([x.to_dict(has_items=False) for x in r])


@router.post('')
def redeems_post(
    data: RedeemCreatePayload,
    user: APIUser = Depends(require_api_user(['insert'])),
):
    '''添加redeem，注意可以有items，不存在的item会自动创建'''
    payload = data.model_dump(exclude_none=True)
    with Connect() as c:
        r = Redeem(c).from_dict(payload)
        if r.select_exists():
            raise DataExist(
                f'redeem `{r.code}` already exists')
        r.insert_all()
        return api_success(r.to_dict(has_items='items' in payload))


@router.get('/{code}')
def redeems_redeem_get(
    code: str,
    user: APIUser = Depends(require_api_user(['select'])),
):
    '''查询单个redeem信息'''
    with Connect() as c:
        r = Redeem(c).select(code)
        r.select_items()
        return api_success(r.to_dict())


@router.delete('/{code}')
def redeems_redeem_delete(
    code: str,
    user: APIUser = Depends(require_api_user(['delete'])),
):
    '''删除redeem，会连带删除redeem_item'''
    with Connect() as c:
        Redeem(c).select(code).delete_all()
        return api_success()


@router.put('/{code}')
def redeems_redeem_put(
    code: str,
    data: RedeemUpdatePayload,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''更新redeem信息，注意不能有items'''
    payload = data.to_data()
    if not payload:
        raise InputError('No change', api_error_code=-100)
    with Connect() as c:
        r = Redeem(c).select(code)
        if 'type' in payload:
            r.redeem_type = int(payload['type'])
        r.update()
        return api_success(r.to_dict(has_items=False))


@router.get('/{code}/items')
def redeems_redeem_items_get(
    code: str,
    user: APIUser = Depends(require_api_user(['select'])),
):
    '''查询redeem的items'''
    with Connect() as c:
        r = Redeem(c)
        r.code = code
        r.select_items()
        return api_success([x.to_dict(has_is_available=True) for x in r.items])


@router.patch('/{code}/items')
def redeems_redeem_items_patch(
    code: str,
    data: BatchPatchPayload,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''增删改单个redeem的items'''
    payload = data.to_data()
    if not payload:
        raise InputError('No change', api_error_code=-100)
    with Connect() as c:
        r = Redeem(c)
        r.code = code
        r.select_items()
        r.remove_items([ItemFactory.from_dict(x, c=c)
                        for x in payload.get('remove', [])])
        r.add_items([ItemFactory.from_dict(x, c=c)
                     for x in payload.get('create', [])])

        updates = payload.get('update', [])
        for x in updates:
            if 'amount' not in x:
                raise InputError('`amount` is required in `update`')
            if not isinstance(x['amount'], int) or x['amount'] <= 0:
                raise InputError(
                    '`amount` must be a positive integer', api_error_code=-101)

        r.update_items([ItemFactory.from_dict(x, c=c) for x in updates])
        return api_success([x.to_dict(has_is_available=True) for x in r.items])
