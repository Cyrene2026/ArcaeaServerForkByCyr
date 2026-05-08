import json
import inspect
from time import perf_counter
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from starlette.datastructures import QueryParams

from core.bundle import BundleDownload
from core.character import UserCharacter
from core.download import DownloadList
from core.error import ArcError, RateLimit
from core.item import ItemCharacter
from core.notification import NotificationFactory
from core.sql import Connect
from core.system import GameInfo
from core.user import UserOnline

from .native import authed_user_id, game_error, game_success, is_error_response, logger, server_try
from .present import present_info
from .purchase import bundle_bundle, bundle_pack, get_single
from .score import song_score_friend
from .user import user_me
from .world import world_all

router = APIRouter(tags=['game-others'])


class AggregateRequest:
    def __init__(self, params: QueryParams) -> None:
        self.query_params = params


def _parse_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return json.loads(value)


def _response_json(response) -> dict:
    if isinstance(response, JSONResponse):
        return json.loads(response.body.decode() or '{}')
    return response


async def _resolve_response(response):
    if inspect.isawaitable(response):
        response = await response
    return _response_json(response)


def _download_song(params: QueryParams, user_id: int):
    with Connect(in_memory=True) as c_m:
        with Connect() as c:
            x = DownloadList(c_m, UserOnline(c, user_id))
            x.song_ids = params.getlist('sid')
            x.url_flag = _parse_bool(params.get('url'), True)
            if x.url_flag and x.is_limited:
                raise RateLimit('You have reached the download limit.', 903)

            x.add_songs()
            return game_success(x.urls)


@router.get('/game/info')
def game_info():
    return game_success(GameInfo().to_dict())


@router.get('/notification/me')
@server_try
def notification_me(user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect(in_memory=True) as c_m:
        x = NotificationFactory(c_m, UserOnline(c_m, user_id))
        return game_success([i.to_dict() for i in x.get_notification()])


@router.get('/game/content_bundle')
@server_try
def game_content_bundle(request: Request):
    trace_id = uuid4().hex[:12]
    start_time = perf_counter()
    app_version = request.headers.get('AppVersion')
    bundle_version = request.headers.get('ContentBundle')
    device_id = request.headers.get('DeviceId')
    logger.info(
        '[content_bundle:%s] request start ip=%s app_version=%s content_bundle=%s device_id=%s user_agent=%s',
        trace_id,
        request.client.host if request.client else '',
        app_version,
        bundle_version,
        device_id,
        request.headers.get('User-Agent'),
    )
    with Connect(in_memory=True) as c_m:
        x = BundleDownload(c_m, trace_id=trace_id)
        x.set_client_info(app_version, bundle_version, device_id)
        bundles = x.get_bundle_list()
        versions = [i.get('contentBundleVersion') for i in bundles]
        logger.info(
            '[content_bundle:%s] response bundle_count=%s versions=%s elapsed_ms=%.2f',
            trace_id,
            len(bundles),
            versions,
            (perf_counter() - start_time) * 1000,
        )
        return game_success({'orderedResults': bundles})


@router.get('/serve/download/me/song')
@server_try
def download_song(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    return _download_song(request.query_params, user_id)


@router.get('/finale/progress')
def finale_progress():
    return game_success({'percentage': 100000})


@router.post('/finale/finale_start')
@server_try
def finale_start(user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        item = ItemCharacter(c)
        item.set_id('55')
        item.user_claim_item(UserOnline(c, user_id))
        return game_success({})


@router.post('/finale/finale_end')
@server_try
def finale_end(user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        item = ItemCharacter(c)
        item.set_id('5')
        item.user_claim_item(UserOnline(c, user_id))
        return game_success({})


@router.post('/insight/me/complete/{pack_id}')
@server_try
def insight_complete(pack_id: str, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        u = UserOnline(c, user_id)
        if pack_id == 'eden_append_1':
            item = ItemCharacter(c)
            item.set_id('72')
            item.user_claim_item(u)
            u.update_user_one_column('insight_state', 1)
        elif pack_id == 'lephon':
            u.update_user_one_column('insight_state', 3)
        else:
            raise ArcError('Invalid pack_id', 151, status=404)

        return game_success({'insight_state': u.insight_state})


@router.post('/unlock/me/awaken_maya')
@server_try
def awaken_maya(user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        ch = UserCharacter(c, 71, UserOnline(c, user_id))
        ch.select_character_info()
        try:
            ch.character_uncap()
        except ArcError:
            pass

        return game_success({
            'user_id': user_id,
            'updated_characters': [ch.to_dict()],
        })


@router.post('/applog/me/log')
def applog_me():
    return game_success({})


def _aggregate_map(endpoint: str, user_id: int):
    parsed = urlparse(endpoint)
    params = QueryParams([
        (key, item)
        for key, values in parse_qs(parsed.query).items()
        for item in values
    ])
    fake_request = AggregateRequest(params)
    return {
        '/user/me': lambda: user_me(user_id=user_id),
        '/purchase/bundle/pack': lambda: bundle_pack(user_id=user_id),
        '/serve/download/me/song': lambda: _download_song(params, user_id),
        '/game/info': game_info,
        '/present/me': lambda: present_info(user_id=user_id),
        '/world/map/me': lambda: world_all(user_id=user_id),
        '/score/song/friend': lambda: song_score_friend(request=fake_request, user_id=user_id),
        '/purchase/bundle/bundle': bundle_bundle,
        '/finale/progress': finale_progress,
        '/purchase/bundle/single': lambda: get_single(user_id=user_id),
    }[parsed.path]()


@router.get('/compose/aggregate')
@server_try
async def aggregate(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    try:
        get_list = json.loads(request.query_params.get('calls'))
        if len(get_list) > 10:
            return game_error()

        response = {'success': True, 'value': []}
        for call in get_list:
            data = await _resolve_response(_aggregate_map(call['endpoint'], user_id))
            if isinstance(data, dict) and data.get('success') is False:
                error = {
                    'success': False,
                    'error_code': data.get('error_code'),
                    'id': call['id'],
                }
                if 'extra' in data:
                    error['extra'] = data['extra']
                return JSONResponse(error)

            response['value'].append({
                'id': call.get('id'),
                'value': data['value'] if isinstance(data, dict) and 'value' in data else data,
            })

        return JSONResponse(response)
    except (KeyError, TypeError, json.JSONDecodeError):
        return game_error()
