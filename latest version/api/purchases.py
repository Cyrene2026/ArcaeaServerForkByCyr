from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from core.api_user import APIUser
from core.error import DataExist, InputError, NoData
from core.item import ItemFactory
from core.purchase import Purchase
from core.sql import Connect, Query, Sql

from .native import BatchPatchPayload, QueryPayload, api_success, require_api_user

router = APIRouter(prefix='/purchases', tags=['purchases'])


class PurchaseCreatePayload(BaseModel):
    purchase_name: Any
    orig_price: Any
    price: Any = None
    discount_from: Any = None
    discount_to: Any = None
    discount_reason: Any = None
    items: Any = None

    model_config = ConfigDict(extra='ignore')


class PurchaseUpdatePayload(BaseModel):
    price: Any = None
    orig_price: Any = None
    discount_from: Any = None
    discount_to: Any = None
    discount_reason: Any = None

    model_config = ConfigDict(extra='ignore')

    def to_data(self) -> dict:
        return {key: getattr(self, key) for key in self.model_fields_set}


@router.get('')
def purchases_get(
    data: QueryPayload = Depends(),
    user: APIUser = Depends(require_api_user(['select'])),
):
    '''查询全部购买信息'''
    with Connect() as c:
        query = Query(['purchase_name', 'discount_reason'], ['purchase_name'], [
                      'purchase_name', 'price', 'orig_price', 'discount_from', 'discount_to']).from_dict(data.to_data())
        x = Sql(c).select('purchase', query=query)
        r = [Purchase().from_list(i) for i in x]

        if not r:
            raise NoData(api_error_code=-2)

        return api_success([x.to_dict(has_items=False, show_real_price=False) for x in r])


@router.post('')
def purchases_post(
    data: PurchaseCreatePayload,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''新增购买，注意可以有items，不存在的item会自动创建'''
    payload = data.model_dump(exclude_none=True)
    with Connect() as c:
        purchase = Purchase(c).from_dict(payload)
        if purchase.select_exists():
            raise DataExist(
                f'Purchase `{purchase.purchase_name}` already exists')
        purchase.insert_all()
        return api_success(purchase.to_dict(has_items='items' in payload, show_real_price=False))


@router.get('/{purchase_name}')
def purchases_purchase_get(
    purchase_name: str,
    user: APIUser = Depends(require_api_user(['select'])),
):
    '''查询单个购买信息'''
    with Connect() as c:
        return api_success(Purchase(c).select(purchase_name).to_dict(show_real_price=False))


@router.delete('/{purchase_name}')
def purchases_purchase_delete(
    purchase_name: str,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''删除单个购买信息，会连带删除purchase_item'''
    with Connect() as c:
        Purchase(c).select(purchase_name).delete_all()
        return api_success()


@router.put('/{purchase_name}')
def purchases_purchase_put(
    purchase_name: str,
    data: PurchaseUpdatePayload,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''修改单个购买信息，注意不能有items'''
    payload = data.to_data()
    if not payload:
        raise InputError('No change', api_error_code=-100)
    with Connect() as c:
        purchase = Purchase(c).select(purchase_name)
        t = ['price', 'orig_price', 'discount_from', 'discount_to']
        for i in t:
            if i in payload:
                setattr(purchase, i, int(payload[i]))
        if 'discount_reason' in payload:
            purchase.discount_reason = str(payload['discount_reason'])

        purchase.update()
        return api_success(purchase.to_dict(has_items=False, show_real_price=False))


@router.get('/{purchase_name}/items')
def purchases_purchase_items_get(
    purchase_name: str,
    user: APIUser = Depends(require_api_user(['select'])),
):
    '''查询单个购买的所有items'''
    with Connect() as c:
        p = Purchase(c)
        p.purchase_name = purchase_name
        p.select_items()
        return api_success([x.to_dict(has_is_available=True) for x in p.items])


@router.patch('/{purchase_name}/items')
def purchases_purchase_items_patch(
    purchase_name: str,
    data: BatchPatchPayload,
    user: APIUser = Depends(require_api_user(['change'])),
):
    '''增删改单个购买的批量items'''
    payload = data.to_data()
    if not payload:
        raise InputError('No change', api_error_code=-100)
    with Connect() as c:
        p = Purchase(c)
        p.purchase_name = purchase_name
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
