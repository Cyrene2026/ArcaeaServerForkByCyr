from fastapi import APIRouter

from core.config_manager import Config

from . import (auth, course, friend, mission, multiplayer, others, present,
               purchase, score, user, world)
from .native import game_error, game_responses, string_to_list


def _server_router() -> APIRouter:
    router = APIRouter()
    for child in (
        user.account_router,
        user.router,
        auth.router,
        friend.router,
        score.router,
        world.router,
        purchase.router,
        present.router,
        others.router,
        multiplayer.router,
        course.router,
        mission.router,
    ):
        router.include_router(child, responses=game_responses)
    return router


def _old_router() -> APIRouter:
    router = APIRouter()

    @router.api_route('/{any:path}', methods=['GET', 'POST'])
    def server_hello(any: str):
        return game_error()

    return router


def register_routers(app) -> None:
    server_router = _server_router()
    for prefix in string_to_list(Config.GAME_API_PREFIX):
        app.include_router(server_router, prefix=prefix.rstrip('/'))

    old_router = _old_router()
    for prefix in string_to_list(Config.OLD_GAME_API_PREFIX):
        app.include_router(old_router, prefix=prefix.rstrip('/'))
