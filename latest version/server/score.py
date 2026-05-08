from random import randint
from time import time

<<<<<<< HEAD
from fastapi import APIRouter, Depends
=======
from fastapi import APIRouter, Depends, Request
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979

from core.constant import Constant
from core.course import CoursePlay
from core.error import InputError
from core.rank import RankList
from core.score import UserPlay
from core.sql import Connect
from core.user import UserOnline

<<<<<<< HEAD
from .native import authed_user_id, game_success, is_error_response, server_try
from .schemas import ScoreTokenCourseQuery, ScoreTokenWorldQuery, SongScorePostForm, SongScoreQuery
=======
from .native import authed_user_id, form_data, form_get, game_success, is_error_response, query_get, server_try
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979

router = APIRouter(prefix='/score', tags=['game-score'])


@router.get('/token')
def score_token():
    return game_success({'token': '1145141919810'})


@router.get('/token/world')
@server_try
<<<<<<< HEAD
def score_token_world(data: ScoreTokenWorldQuery = Depends(), user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    stamina_multiply = data.stamina_multiply
    fragment_multiply = data.fragment_multiply
    prog_boost_multiply = data.prog_boost_multiply
    beyond_boost_gauge_use = data.beyond_boost_gauge_use
    skill_cytusii_flag = None
    skill_chinatsu_flag = None
    skill_id = data.skill_id

    if (skill_id == 'skill_ilith_ivy' or skill_id == 'skill_hikari_vanessa') and data.is_skill_sealed == 'false':
        skill_cytusii_flag = ''.join([str(randint(0, 2)) for _ in range(5)])
    if skill_id == 'skill_chinatsu' and data.is_skill_sealed == 'false':
=======
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
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
        skill_chinatsu_flag = ''.join([str(randint(0, 2)) for _ in range(7)])
    skill_flag = skill_cytusii_flag or skill_chinatsu_flag

    with Connect() as c:
        x = UserPlay(c, UserOnline(c, user_id))
<<<<<<< HEAD
        x.song.set_chart(data.song_id, data.difficulty)
=======
        x.song.set_chart(query_get(request, 'song_id'), query_get(request, 'difficulty', type=int))
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
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
<<<<<<< HEAD
def score_token_course(data: ScoreTokenCourseQuery = Depends(), user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        use_course_skip_purchase = data.use_course_skip_purchase == 'true'
        user = UserOnline(c, user_id)
        user_play = UserPlay(c, user)
        user_play.song_token = data.previous_token
=======
def score_token_course(request: Request, user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        use_course_skip_purchase = query_get(
            request, 'use_course_skip_purchase', 'false') == 'true'
        user = UserOnline(c, user_id)
        user_play = UserPlay(c, user)
        user_play.song_token = query_get(request, 'previous_token', None)
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
        user_play.get_play_state()
        status = 'created'
        if user_play.course_play_state == -1:
            course_play = CoursePlay(c, user, user_play)
<<<<<<< HEAD
            course_play.course_id = data.course_id
=======
            course_play.course_id = request.query_params['course_id']
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
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
<<<<<<< HEAD
async def song_score_post(payload: SongScorePostForm = Depends(SongScorePostForm.as_form), user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        x = UserPlay(c, UserOnline(c, user_id))
        x.song_token = payload.song_token
        x.song_hash = payload.song_hash
        x.song.set_chart(payload.song_id, payload.difficulty)
        x.set_score(payload.score, payload.shiny_perfect_count, payload.perfect_count, payload.near_count,
                    payload.miss_count, payload.health, payload.modifier, int(time() * 1000), payload.clear_type)
        x.beyond_gauge = payload.beyond_gauge
        x.submission_hash = payload.submission_hash
        x.combo_interval_bonus = payload.combo_interval_bonus
        x.hp_interval_bonus = payload.hp_interval_bonus
        x.fever_bonus = payload.fever_bonus
        x.rank_bonus = payload.rank_bonus
        x.maya_gauge = payload.maya_gauge
        x.nextstage_bonus = payload.nextstage_bonus
        x.highest_health = payload.highest_health
        x.lowest_health = payload.lowest_health
        x.room_code = payload.room_code
        x.room_total_score = payload.room_total_score
        x.room_total_players = payload.room_total_players
=======
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
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
        if not x.is_valid:
            raise InputError('Invalid score.', 107)
        x.upload_score()
        return game_success(x.to_dict())


@router.get('/song')
@server_try
<<<<<<< HEAD
def song_score_top(data: SongScoreQuery = Depends(), user_id=Depends(authed_user_id)):
=======
def song_score_top(request: Request, user_id=Depends(authed_user_id)):
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        rank_list = RankList(c)
<<<<<<< HEAD
        rank_list.song.set_chart(data.song_id, data.difficulty)
=======
        rank_list.song.set_chart(query_get(request, 'song_id'), query_get(request, 'difficulty'))
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
        rank_list.select_top()
        return game_success(rank_list.to_dict_list())


@router.get('/song/me')
@server_try
<<<<<<< HEAD
def song_score_me(data: SongScoreQuery = Depends(), user_id=Depends(authed_user_id)):
=======
def song_score_me(request: Request, user_id=Depends(authed_user_id)):
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        rank_list = RankList(c)
<<<<<<< HEAD
        rank_list.song.set_chart(data.song_id, data.difficulty)
=======
        rank_list.song.set_chart(query_get(request, 'song_id'), query_get(request, 'difficulty'))
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
        rank_list.select_me(UserOnline(c, user_id))
        return game_success(rank_list.to_dict_list())


@router.get('/song/friend')
@server_try
<<<<<<< HEAD
def song_score_friend(data: SongScoreQuery = Depends(), user_id=Depends(authed_user_id)):
=======
def song_score_friend(request: Request, user_id=Depends(authed_user_id)):
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        rank_list = RankList(c)
<<<<<<< HEAD
        rank_list.song.set_chart(data.song_id, data.difficulty)
=======
        rank_list.song.set_chart(query_get(request, 'song_id'), query_get(request, 'difficulty'))
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
        rank_list.select_friend(UserOnline(c, user_id))
        return game_success(rank_list.to_dict_list())
