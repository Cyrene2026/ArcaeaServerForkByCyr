from . import (users, songs, token, system, items,
               purchases, presents, redeems, characters, multiplay)
<<<<<<< HEAD
from .native import api_responses, install_native_api_handlers
=======
from .native import install_native_api_handlers
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979


def register_routers(app):
    install_native_api_handlers(app)
    for module in (token, users, items, songs, purchases, presents, redeems, system, characters, multiplay):
<<<<<<< HEAD
        app.include_router(module.router, prefix='/api/v1', responses=api_responses)
=======
        app.include_router(module.router, prefix='/api/v1')
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979
