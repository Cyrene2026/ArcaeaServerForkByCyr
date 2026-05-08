import re

from fastapi.routing import APIRoute

from . import index, login


def _register_url_for_routes(app, endpoint_prefix: str, router) -> None:
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        path = route.path_format
        endpoint = f"{endpoint_prefix}.{route.name}"
        app._routes[endpoint] = path
        app._route_params[endpoint] = re.findall(r"\{([^}:]+)(?::[^}]+)?\}", path)


def register_routers(app) -> None:
    app.fastapi_app.include_router(login.router)
    app.fastapi_app.include_router(index.router)
    _register_url_for_routes(app, 'login', login.router)
    _register_url_for_routes(app, 'index', index.router)
