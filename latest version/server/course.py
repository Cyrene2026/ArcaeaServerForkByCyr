from fastapi import APIRouter, Depends

from core.constant import Constant
from core.course import UserCourseList
from core.item import ItemCore
from core.sql import Connect
from core.user import UserOnline

from .native import authed_user_id, game_success, is_error_response, server_try

router = APIRouter(prefix='/course', tags=['game-course'])


@router.get('/me')
@server_try
def course_me(user_id=Depends(authed_user_id)):
    if is_error_response(user_id):
        return user_id
    with Connect() as c:
        user = UserOnline(c, user_id)
        core = ItemCore(c)
        core.item_id = 'core_course_skip_purchase'
        core.select_user_item(user)
        x = UserCourseList(c, user)
        x.select_all()
        return game_success({
            'courses': x.to_dict_list(),
            "stamina_cost": Constant.COURSE_STAMINA_COST,
            "course_skip_purchase_ticket": core.amount
        })
