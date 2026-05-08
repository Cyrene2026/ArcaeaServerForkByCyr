from time import time

from fastapi import APIRouter, Depends

from core.constant import Constant
from core.error import InputError, ItemUnavailable
from core.item import ItemFactory, Stamina6
from core.purchase import Purchase, PurchaseList
from core.redeem import UserRedeem
from core.sql import Connect
from core.user import UserOnline

from .native import authed_user_id, game_success, is_error_response, server_try
from .schemas import PurchaseItemForm, PurchasePackForm, RedeemCodeForm

router = APIRouter(prefix='/purchase', tags=['game-purchase'])


@router.get('/bundle/pack')
@server_try
def bundle_pack(user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        x = PurchaseList(c, UserOnline(c, user_id)).select_from_type('pack')
        return game_success(x.to_dict_list())


@router.get('/bundle/single')
@server_try
def get_single(user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        x = PurchaseList(c, UserOnline(c, user_id)).select_from_type('single')
        return game_success(x.to_dict_list())


@router.get('/bundle/bundle')
def bundle_bundle():
    return game_success([])


@router.post('/me/pack')
@server_try
async def buy_pack_or_single(payload: PurchasePackForm = Depends(PurchasePackForm.as_form), user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        if payload.pack_id is not None:
            purchase_name = payload.pack_id
        elif payload.single_id is not None:
            purchase_name = payload.single_id
        else:
            return game_success()

        x = Purchase(c, UserOnline(c, user_id)).select(purchase_name)
        x.buy()
        return game_success({
            'user_id': x.user.user_id,
            'ticket': x.user.ticket,
            'packs': x.user.packs,
            'singles': x.user.singles,
            'characters': x.user.characters_list
        })


@router.post('/me/item')
@server_try
async def buy_special(payload: PurchaseItemForm = Depends(PurchaseItemForm.as_form), user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        item_id = payload.item_id
        x = Purchase(c, UserOnline(c, user_id))
        x.purchase_name = item_id
        x.price = 50
        x.orig_price = 50
        x.discount_from = -1
        x.discount_to = -1
        x.items = [ItemFactory(c).get_item(item_id)]
        x.buy()
        r = {'user_id': x.user.user_id, 'ticket': x.user.ticket}
        if item_id == 'stamina6':
            r['stamina'] = x.user.stamina.stamina
            r['max_stamina_ts'] = x.user.stamina.max_stamina_ts
            r['world_mode_locked_end_ts'] = -1
        return game_success(r)


@router.post('/me/stamina/{buy_stamina_type}')
@server_try
def purchase_stamina(buy_stamina_type: str, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        if buy_stamina_type != 'fragment':
            raise InputError('Invalid type of buying stamina')
        user = UserOnline(c, user_id)
        user.select_user_one_column('next_fragstam_ts', -1)
        now = int(time() * 1000)
        if user.next_fragstam_ts > now:
            raise ItemUnavailable('Buying stamina by fragment is not available yet.', 905)
        user.update_user_one_column(
            'next_fragstam_ts', now + Constant.FRAGSTAM_RECOVER_TICK)
        s = Stamina6(c)
        s.user_claim_item(user)
        return game_success({
            "user_id": user.user_id,
            "stamina": user.stamina.stamina,
            "max_stamina_ts": user.stamina.max_stamina_ts,
            "next_fragstam_ts": user.next_fragstam_ts,
            'world_mode_locked_end_ts': -1
        })


@router.post('/me/redeem')
@server_try
async def redeem(payload: RedeemCodeForm = Depends(RedeemCodeForm.as_form), user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        x = UserRedeem(c, UserOnline(c, user_id))
        x.claim_user_redeem(payload.code)
        return game_success({"coupon": "fragment" + str(x.fragment) if x.fragment > 0 else ""})
