from fastapi import APIRouter, Depends, Request

from core.config_manager import Config
from core.error import ArcError
from core.linkplay import MatchStore, Player, RemoteMultiPlayer, Room
from core.notification import RoomInviteNotification
from core.sql import Connect

from .native import authed_user_id, form_data, form_get, game_success, is_error_response, server_try

router = APIRouter(prefix='/multiplayer', tags=['game-multiplayer'])


def _linkplay_endpoint(request: Request) -> dict:
    return {
        'endPoint': request.headers.get('host', '').split(':')[0]
        if Config.LINKPLAY_DISPLAY_HOST == '' else Config.LINKPLAY_DISPLAY_HOST,
        'port': int(Config.LINKPLAY_UDP_PORT),
    }


def _ensure_linkplay_available() -> None:
    if not Config.LINKPLAY_HOST:
        raise ArcError('The link play server is unavailable.', 151, status=404)


@router.post('/me/room/create')
@server_try
async def room_create(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    _ensure_linkplay_available()
    payload = await request.json()
    with Connect() as c:
        x = RemoteMultiPlayer()
        user = Player(c, user_id)
        user.get_song_unlock(payload['clientSongMap'])
        x.create_room(user)
        r = x.to_dict()
        r.update(_linkplay_endpoint(request))
        return game_success(r)


@router.post('/me/room/join/{room_code}')
@server_try
async def room_join(room_code: str, request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    _ensure_linkplay_available()
    payload = await request.json()
    with Connect() as c:
        x = RemoteMultiPlayer()
        user = Player(c, user_id)
        user.get_song_unlock(payload['clientSongMap'])
        room = Room()
        room.room_code = room_code
        x.join_room(room, user)
        r = x.to_dict()
        r.update(_linkplay_endpoint(request))
        return game_success(r)


@router.post('/me/update')
@server_try
async def multiplayer_update(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    _ensure_linkplay_available()
    payload = await request.json()
    with Connect() as c:
        x = RemoteMultiPlayer()
        user = Player(c, user_id)
        user.token = int(payload['token'])
        x.update_room(user)
        r = x.to_dict()
        r.update(_linkplay_endpoint(request))
        return game_success(r)


@router.post('/me/room/{room_code}/invite')
@server_try
async def room_invite(room_code: str, request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    _ensure_linkplay_available()
    form = await form_data(request)
    other_user_id = form_get(form, 'to', type=int)

    x = RemoteMultiPlayer()
    share_token = x.select_room(room_code=room_code)['share_token']

    with Connect(in_memory=True) as c_m:
        with Connect() as c:
            sender = Player(c, user_id)
            sender.select_user_about_link_play()
            n = RoomInviteNotification.from_sender(
                sender, Player(c, other_user_id), share_token, c_m)
            n.insert()

    return game_success({})


@router.post('/me/room/status')
@server_try
async def room_status(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    _ensure_linkplay_available()
    form = await form_data(request)
    share_token = form_get(form, 'shareToken', type=str)

    x = RemoteMultiPlayer()
    room_code = x.select_room(share_token=share_token)['room_code']

    return game_success({'roomId': room_code})


@router.post('/me/matchmaking/join/')
@server_try
async def matchmaking_join(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    _ensure_linkplay_available()
    payload = await request.json()
    with Connect() as c:
        user = Player(None, user_id)
        user.get_song_unlock(payload['clientSongMap'])

        x = MatchStore(c)
        x.init_player(user)
        r = x.match(user_id)

        if r is None:
            return game_success({
                'userId': user_id,
                'status': 2,
            })

        r.update(_linkplay_endpoint(request))
        return game_success(r)


@router.post('/me/matchmaking/status/')
@server_try
def matchmaking_status(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    _ensure_linkplay_available()
    with Connect() as c:
        r = MatchStore(c).match(user_id)
        if r is None:
            return game_success({
                'userId': user_id,
                'status': 0,
            })

        r.update(_linkplay_endpoint(request))
        return game_success(r)


@router.post('/me/matchmaking/leave/')
@server_try
def matchmaking_leave(user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    _ensure_linkplay_available()
    MatchStore().clear_player(user_id)
    return game_success({})
