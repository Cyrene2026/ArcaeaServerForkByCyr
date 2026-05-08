import logging

from fastapi import APIRouter, Depends, Request

from core.character import UserCharacter
from core.config_manager import Config
from core.error import ArcError
from core.item import ItemCore
from core.operation import DeleteOneUser
from core.save import SaveData
from core.sql import Connect
from core.user import User, UserLogin, UserOnline, UserRegister

from .native import authed_user_id, form_data, form_get, game_success, header_check, is_error_response, server_try
<<<<<<< HEAD
from .schemas import CharacterChangeForm, CharacterExpForm, GameRegisterForm, UserSettingForm
=======
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979

router = APIRouter(prefix='/user', tags=['game-user'])
account_router = APIRouter(prefix='/account', tags=['game-account'])
logger = logging.getLogger('main')


<<<<<<< HEAD
async def _register_impl(request: Request, payload: GameRegisterForm):
    error = header_check(request)
    if error is not None:
        raise error
    with Connect() as c:
        new_user = UserRegister(c)
        new_user.set_name(payload.name)
        new_user.set_password(payload.password)
        new_user.set_email(payload.email)
        device_id = payload.device_id
        if payload.is_allow_marketing_email is not None:
            new_user.is_allow_marketing_email = payload.is_allow_marketing_email == 'true'
=======
async def _register_impl(request: Request):
    error = header_check(request)
    if error is not None:
        raise error
    form = await form_data(request)
    with Connect() as c:
        new_user = UserRegister(c)
        new_user.set_name(form['name'])
        new_user.set_password(form['password'])
        new_user.set_email(form['email'])
        device_id = form['device_id'] if 'device_id' in form else 'low_version'
        if 'is_allow_marketing_email' in form:
            new_user.is_allow_marketing_email = form['is_allow_marketing_email'] == 'true'
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
        ip = request.client.host if request.client else ''
        new_user.register(device_id, ip)
        user = UserLogin(c)
        user.login(new_user.name, new_user.password, device_id, ip)
        logger.info(f'New user `{user.user_id}` registered')
        return game_success({'user_id': user.user_id, 'access_token': user.token})


@router.post('')
@account_router.post('')
@server_try
<<<<<<< HEAD
async def register(request: Request, payload: GameRegisterForm = Depends(GameRegisterForm.as_form)):
    return await _register_impl(request, payload)
=======
async def register(request: Request):
    return await _register_impl(request)
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979


@router.get('/me')
@server_try
def user_me(user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        return game_success(UserOnline(c, user_id).to_dict())


@router.post('/me/toggle_invasion')
@server_try
def toggle_invasion(user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        user = UserOnline(c, user_id)
        user.toggle_invasion()
        return game_success({'user_id': user.user_id, 'insight_state': user.insight_state})


@router.post('/me/character')
@server_try
<<<<<<< HEAD
async def character_change(payload: CharacterChangeForm = Depends(CharacterChangeForm.as_form), user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        user = UserOnline(c, user_id)
        user.change_character(payload.character, payload.skill_sealed == 'true')
=======
async def character_change(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    form = await form_data(request)
    with Connect() as c:
        user = UserOnline(c, user_id)
        user.change_character(
            int(form['character']), form['skill_sealed'] == 'true')
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
        return game_success({'user_id': user.user_id, 'character': user.character.character_id})


@router.post('/me/character/{character_id}/toggle_uncap')
@server_try
def toggle_uncap(character_id: int, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        user = User()
        user.user_id = user_id
        character = UserCharacter(c, character_id)
        character.change_uncap_override(user)
        character.select_character_info(user)
        return game_success({'user_id': user.user_id, 'character': [character.to_dict()]})


@router.post('/me/character/{character_id}/uncap')
@server_try
def character_first_uncap(character_id: int, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        user = UserOnline(c, user_id)
        character = UserCharacter(c, character_id)
        character.select_character_info(user)
        character.character_uncap(user)
        return game_success({'user_id': user.user_id, 'character': [character.to_dict()], 'cores': user.cores})


@router.post('/me/character/{character_id}/exp')
@server_try
<<<<<<< HEAD
async def character_exp(
    character_id: int,
    payload: CharacterExpForm = Depends(CharacterExpForm.as_form),
    user_id=Depends(authed_user_id),
):
    if is_error_response(user_id):
        return user_id
=======
async def character_exp(request: Request, character_id: int, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    form = await form_data(request)
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
    with Connect() as c:
        user = UserOnline(c, user_id)
        character = UserCharacter(c, character_id)
        character.select_character_info(user)
        core = ItemCore(c)
<<<<<<< HEAD
        core.amount = -payload.amount
=======
        core.amount = - int(form['amount'])
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
        core.item_id = 'core_generic'
        character.upgrade_by_core(user, core)
        return game_success({'user_id': user.user_id, 'character': [character.to_dict()], 'cores': user.cores})


@router.get('/me/save')
@server_try
def cloud_get(user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        user = User()
        user.user_id = user_id
        save = SaveData(c)
        save.select_all(user)
        return game_success(save.to_dict())


@router.post('/me/save')
@server_try
async def cloud_post(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    form = await form_data(request)
    with Connect() as c:
        user = User()
        user.user_id = user_id
        save = SaveData(c)
        save.set_value('scores_data', form['scores_data'], form['scores_checksum'])
        save.set_value('clearlamps_data', form['clearlamps_data'], form['clearlamps_checksum'])
        save.set_value('clearedsongs_data', form['clearedsongs_data'], form['clearedsongs_checksum'])
        save.set_value('unlocklist_data', form['unlocklist_data'], form['unlocklist_checksum'])
        save.set_value('installid_data', form['installid_data'], form['installid_checksum'])
        save.set_value('devicemodelname_data', form['devicemodelname_data'], form['devicemodelname_checksum'])
        save.set_value('story_data', form['story_data'], form['story_checksum'])
        save.set_value('finalestate_data', form_get(form, 'finalestate_data'), form_get(form, 'finalestate_checksum'))
        save.update_all(user)
        return game_success({'user_id': user.user_id})


@router.post('/me/profile')
@server_try
async def profile_post(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    form = await form_data(request)
    with Connect() as c:
        user = UserOnline(c, user_id)
        is_profile_public = form_get(form, 'is_profile_public')
        banner = form_get(form, 'banner')
        user.select_user_about_profile()
        user.change_profile(is_profile_public == 'true', banner)
        return game_success({
            "is_profile_public": user.is_profile_public,
            "showcase_characters": [-1, -1, -1],
            "world_unlock": "",
            "custom_banner": user.custom_banner
        })


@router.post('/me/setting/{set_arg}')
@server_try
<<<<<<< HEAD
async def sys_set(
    set_arg: str,
    payload: UserSettingForm = Depends(UserSettingForm.as_form),
    user_id=Depends(authed_user_id),
):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        value = payload.value
=======
async def sys_set(request: Request, set_arg: str, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    form = await form_data(request)
    with Connect() as c:
        value = form['value']
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
        user = UserOnline(c, user_id)
        if 'favorite_character' == set_arg:
            user.change_favorite_character(int(value))
        else:
            value = 'true' == value
            if set_arg in ('is_hide_rating', 'max_stamina_notification_enabled', 'mp_notification_enabled', 'is_allow_marketing_email'):
                user.update_user_one_column(set_arg, value)
        return game_success(user.to_dict())


async def _user_delete_impl(user_id):
    if is_error_response(user_id):
        return user_id
    if not Config.ALLOW_SELF_ACCOUNT_DELETE:
        raise ArcError('Cannot delete the account.', 151, status=404)
    DeleteOneUser().set_params(user_id).run()
    return game_success({'user_id': user_id})


@router.post('/me/request_delete')
@account_router.post('/me/request_delete')
@server_try
async def user_delete(user_id=Depends(authed_user_id)):
    return await _user_delete_impl(user_id)


@router.post('/email/resend_verify')
@account_router.post('/email/resend_verify')
@server_try
def email_resend_verify():
    raise ArcError('Email verification unavailable.', 151, status=404)


@router.post('/verify')
@account_router.post('/verify')
@server_try
def email_verify():
    raise ArcError('Email verification unavailable.', 151, status=404)
