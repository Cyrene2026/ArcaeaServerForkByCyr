from . import (users, songs, token, system, items,
               purchases, presents, redeems, characters, multiplay)
from .native import api_responses, install_native_api_handlers


def register_routers(app):
    install_native_api_handlers(app)
    for module in (token, users, items, songs, purchases, presents, redeems, system, characters, multiplay):
        app.include_router(module.router, prefix='/api/v1', responses=api_responses)
