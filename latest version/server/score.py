from random import randint
from time import time

from fastapi import APIRouter, Depends, Request

from core.constant import Constant
from core.course import CoursePlay
from core.error import InputError
from core.rank import RankList
from core.score import UserPlay
from core.sql import Connect
from core.user import UserOnline

from .native import authed_user_id, form_data, form_get, game_success, is_error_response, query_get, server_try

router = APIRouter(prefix='/score', tags=['game-score'])


@router.get('/token')
def score_token():
    return game_success({'token': '1145141919810'})


@router.get('/token/world')
@server_try
def score_token_world(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    stamina_multiply = query_get(request, 'stamina_multiply', 1, int)
    fragment_multiply = query_get(request, 'fragment_multiply', 100, int)
    prog_boost_multiply = query_get(request, 'prog_boost_multiply', 0, int)
    beyond_boost_gauge_use = query_get(request, 'beyond_boost_gauge_use', 0, int)
    skill_cytusii_flag = None
    skill_chinatsu_flag = None
    skill_id = query_get(request, 'skill_id')

    if (skill_id == 'skill_ilith_ivy' or skill_id == 'skill_hikari_vanessa') and query_get(request, 'is_skill_sealed') == 'false':
        skill_cytusii_flag = ''.join([str(randint(0, 2)) for _ in range(5)])
    if skill_id == 'skill_chinatsu' and query_get(request, 'is_skill_sealed') == 'false':
        skill_chinatsu_flag = ''.join([str(randint(0, 2)) for _ in range(7)])
    skill_flag = skill_cytusii_flag or skill_chinatsu_flag

    with Connect() as c:
        x = UserPlay(c, UserOnline(c, user_id))
        x.song.set_chart(query_get(request, 'song_id'), query_get(request, 'difficulty', type=int))
        x.set_play_state_for_world(
            stamina_multiply, fragment_multiply, prog_boost_multiply, beyond_boost_gauge_use, skill_cytusii_flag, skill_chinatsu_flag)
        r = {
            "stamina": x.user.stamina.stamina,
            "max_stamina_ts": x.user.stamina.max_stamina_ts,
            "token": x.song_token,
            'play_parameters': {},
        }
        if skill_flag and skill_id:
            r['play_parameters'] = {
                skill_id: list(map(lambda x: Constant.WORLD_VALUE_NAME_ENUM[int(x)], skill_flag)),
            }
        if x.invasion_flag == 1:
            r['play_parameters']['invasion_start'] = True
        elif x.invasion_flag == 2:
            r['play_parameters']['invasion_hard'] = True
        return game_success(r)


@router.get('/token/course')
@server_try
def score_token_course(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        use_course_skip_purchase = query_get(
            request, 'use_course_skip_purchase', 'false') == 'true'
        user = UserOnline(c, user_id)
        user_play = UserPlay(c, user)
        user_play.song_token = query_get(request, 'previous_token', None)
        user_play.get_play_state()
        status = 'created'
        if user_play.course_play_state == -1:
            course_play = CoursePlay(c, user, user_play)
            course_play.course_id = request.query_params['course_id']
            user_play.course_play = course_play
            user_play.set_play_state_for_course(use_course_skip_purchase)
        elif 0 <= user_play.course_play_state <= 3:
            user_play.update_token_for_course()
        else:
            user_play.clear_play_state()
            user.select_user_about_stamina()
            status = 'cleared' if user_play.course_play_state == 4 else 'failed'
        return game_success({
            "stamina": user.stamina.stamina,
            "max_stamina_ts": user.stamina.max_stamina_ts,
            "token": user_play.song_token,
            'status': status
        })


@router.post('/song')
@server_try
async def song_score_post(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    form = await form_data(request)
    with Connect() as c:
        x = UserPlay(c, UserOnline(c, user_id))
        x.song_token = form['song_token']
        x.song_hash = form['song_hash']
        x.song.set_chart(form['song_id'], form['difficulty'])
        x.set_score(form['score'], form['shiny_perfect_count'], form['perfect_count'], form['near_count'],
                    form['miss_count'], form['health'], form['modifier'], int(time() * 1000), form['clear_type'])
        x.beyond_gauge = int(form['beyond_gauge'])
        x.submission_hash = form['submission_hash']
        x.combo_interval_bonus = form_get(form, 'combo_interval_bonus', type=int)
        x.hp_interval_bonus = form_get(form, 'hp_interval_bonus', type=int)
        x.fever_bonus = form_get(form, 'fever_bonus', type=int)
        x.rank_bonus = form_get(form, 'rank_bonus', type=int)
        x.maya_gauge = form_get(form, 'maya_gauge', type=int)
        x.nextstage_bonus = form_get(form, 'nextstage_bonus', type=int)
        x.highest_health = form_get(form, "highest_health", type=int)
        x.lowest_health = form_get(form, "lowest_health", type=int)
        x.room_code = form_get(form, 'room_code')
        x.room_total_score = form_get(form, 'room_total_score', type=int)
        x.room_total_players = form_get(form, 'room_total_players', type=int)
        if not x.is_valid:
            raise InputError('Invalid score.', 107)
        x.upload_score()
        return game_success(x.to_dict())


@router.get('/song')
@server_try
def song_score_top(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        rank_list = RankList(c)
        rank_list.song.set_chart(query_get(request, 'song_id'), query_get(request, 'difficulty'))
        rank_list.select_top()
        return game_success(rank_list.to_dict_list())


@router.get('/song/me')
@server_try
def song_score_me(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        rank_list = RankList(c)
        rank_list.song.set_chart(query_get(request, 'song_id'), query_get(request, 'difficulty'))
        rank_list.select_me(UserOnline(c, user_id))
        return game_success(rank_list.to_dict_list())


@router.get('/song/friend')
@server_try
def song_score_friend(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        rank_list = RankList(c)
        rank_list.song.set_chart(query_get(request, 'song_id'), query_get(request, 'difficulty'))
        rank_list.select_friend(UserOnline(c, user_id))
        return game_success(rank_list.to_dict_list())
