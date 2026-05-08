from __future__ import annotations

import inspect
import json
import logging as py_logging
import os
import re
import uuid
from contextvars import ContextVar
from json import JSONDecodeError
from types import SimpleNamespace
from typing import Any, Callable
from urllib.parse import urlencode

from fastapi import FastAPI as _FastAPI
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel
from starlette.requests import Request as StarletteRequest
from starlette.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)


_current_app: ContextVar["Flask | None"] = ContextVar("current_app", default=None)
_current_request: ContextVar["RequestShim | None"] = ContextVar("request", default=None)
_current_g: ContextVar["G | None"] = ContextVar("g", default=None)
_current_session: ContextVar[dict[str, Any] | None] = ContextVar(
    "session", default=None
)

_sessions: dict[str, dict[str, Any]] = {}


class ConfigDict(dict):
    def from_mapping(self, **kwargs: Any) -> None:
        self.update(kwargs)


class G(SimpleNamespace):
    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class LocalProxy:
    def __init__(self, getter: Callable[[], Any]) -> None:
        object.__setattr__(self, "_getter", getter)

    def _get_current_object(self) -> Any:
        obj = object.__getattribute__(self, "_getter")()
        if obj is None:
            raise RuntimeError("working outside of request/application context")
        return obj

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_current_object(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._get_current_object(), name, value)

    def __getitem__(self, key: str) -> Any:
        return self._get_current_object()[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._get_current_object()[key] = value

    def __contains__(self, key: object) -> bool:
        return key in self._get_current_object()

    def __bool__(self) -> bool:
        return bool(self._get_current_object())


current_app = LocalProxy(lambda: _current_app.get())
request = LocalProxy(lambda: _current_request.get())
g = LocalProxy(lambda: _current_g.get())
session = LocalProxy(lambda: _current_session.get())


class MultiDict(dict):
    def __init__(self, pairs: list[tuple[str, Any]] | dict[str, Any] | None = None) -> None:
        super().__init__()
        self._lists: dict[str, list[Any]] = {}
        if pairs is None:
            return
        if isinstance(pairs, dict):
            pairs = list(pairs.items())
        for key, value in pairs:
            if isinstance(value, list):
                for item in value:
                    self.add(key, item)
            else:
                self.add(key, value)

    def add(self, key: str, value: Any) -> None:
        self._lists.setdefault(key, []).append(value)
        super().__setitem__(key, value)

    def get(self, key: str, default: Any = None, type: Callable | None = None) -> Any:
        value = super().get(key, default)
        if value is default or type is None:
            return value
        try:
            return type(value)
        except (TypeError, ValueError):
            return default

    def getlist(self, key: str) -> list[Any]:
        return list(self._lists.get(key, []))


class FileStorageShim:
    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self._content = content

    def save(self, dst: str) -> None:
        with open(dst, "wb") as f:
            f.write(self._content)


class RequestShim:
    def __init__(
        self,
        request: StarletteRequest,
        body: bytes,
        form: MultiDict,
        files: MultiDict,
        json_data: Any,
        json_error: JSONDecodeError | None = None,
    ) -> None:
        self._request = request
        self._body = body
        self._json = json_data
        self._json_error = json_error
        self.form = form
        self.files = files
        self.args = MultiDict(list(request.query_params.multi_items()))
        self.headers = request.headers
        self.method = request.method
        self.path = request.url.path
        self.url = str(request.url)
        self.host = request.headers.get("host", "")
        self.remote_addr = request.client.host if request.client else ""

    @property
    def data(self) -> bytes:
        return self._body

    @property
    def json(self) -> Any:
        if self._json_error is not None:
            raise self._json_error
        return self._json

    def get_json(self) -> Any:
        if self._json_error is not None:
            raise self._json_error
        return self._json


class CompatJSONResponse(JSONResponse):
    def __init__(self, content: Any, status_code: int = 200, **kwargs: Any) -> None:
        super().__init__(content=content, status_code=status_code, **kwargs)
        self.response = [self.body]


def _dump_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        if hasattr(value, "model_dump"):
            return value.model_dump(exclude_none=True)
        return value.dict(exclude_none=True)
    if isinstance(value, dict):
        return {key: _dump_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_dump_jsonable(item) for item in value]
    return value


def jsonify(*args: Any, **kwargs: Any) -> CompatJSONResponse:
    if args and kwargs:
        raise TypeError("jsonify cannot mix positional and keyword arguments")
    if len(args) == 1:
        content = args[0]
    elif args:
        content = list(args)
    else:
        content = kwargs
    return CompatJSONResponse(_dump_jsonable(content))


def make_response(content: Any = b"", status: int = 200) -> Response:
    return Response(content=content, status_code=status)


def redirect(location: str, code: int = 302) -> RedirectResponse:
    return RedirectResponse(location, status_code=code)


def flash(message: str) -> None:
    store = session._get_current_object()
    store.setdefault("_flashes", []).append(message)


def get_flashed_messages() -> list[str]:
    store = session._get_current_object()
    return list(store.pop("_flashes", []))


def has_app_context() -> bool:
    return _current_app.get() is not None


def _flask_path_to_starlette(path: str) -> tuple[str, list[str]]:
    params: list[str] = []

    def repl(match: re.Match[str]) -> str:
        converter, name = match.group(1), match.group(2)
        params.append(name)
        if converter == "path":
            return f"{{{name}:path}}"
        if converter == "int":
            return f"{{{name}:int}}"
        return f"{{{name}}}"

    converted = re.sub(r"<(?:(string|int|path):)?([a-zA-Z_][a-zA-Z0-9_]*)>", repl, path)
    return converted, params


class Blueprint:
    def __init__(self, name: str, import_name: str, url_prefix: str = "") -> None:
        self.name = name.strip("/") or name
        self.import_name = import_name
        self.url_prefix = url_prefix or ""
        self.routes: list[dict[str, Any]] = []
        self.blueprints: list[Blueprint] = []

    def route(self, rule: str, methods: Any = ("GET",), **options: Any) -> Callable:
        if isinstance(methods, str):
            methods = [methods]
        methods = list(methods)

        def decorator(func: Callable) -> Callable:
            self.routes.append(
                {
                    "rule": rule,
                    "methods": methods,
                    "endpoint": options.get("endpoint") or func.__name__,
                    "func": func,
                }
            )
            return func

        return decorator

    def register_blueprint(self, blueprint: "Blueprint") -> None:
        self.blueprints.append(blueprint)


class Flask:
    def __init__(self, import_name: str) -> None:
        self.import_name = import_name
        self.root_path = os.getcwd()
        self.config = ConfigDict()
        self.logger = py_logging.getLogger(import_name)
        self.fastapi_app = _FastAPI()
        self._routes: dict[str, str] = {}
        self._route_params: dict[str, list[str]] = {}
        self._after_request: list[Callable[[Response], Response]] = []
        self.static_folder = os.path.join(self.root_path, "static")
        if os.path.isdir(self.static_folder):
            self.fastapi_app.mount(
                "/static", StaticFiles(directory=self.static_folder), name="static"
            )
        self._routes["static"] = "/static/{filename:path}"
        self._route_params["static"] = ["filename"]
        self._jinja_env = Environment(
            loader=FileSystemLoader(os.path.join(self.root_path, "templates")),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self._jinja_env.globals.update(
            url_for=url_for, get_flashed_messages=get_flashed_messages, g=g
        )
        _current_app.set(self)

    def __call__(self, scope: dict, receive: Callable, send: Callable) -> Any:
        return self.fastapi_app(scope, receive, send)

    @property
    def router(self) -> Any:
        return self.fastapi_app.router

    def route(self, rule: str, methods: Any = ("GET",), **options: Any) -> Callable:
        bp = Blueprint("", self.import_name)
        decorator = bp.route(rule, methods, **options)

        def register(func: Callable) -> Callable:
            decorator(func)
            route = bp.routes[-1]
            self._add_route(route["rule"], route["methods"], route["endpoint"], route["func"])
            return func

        return register

    def register_blueprint(self, blueprint: Blueprint) -> None:
        self._register_blueprint(blueprint, "", blueprint.name)

    def _register_blueprint(
        self, blueprint: Blueprint, parent_prefix: str, endpoint_prefix: str
    ) -> None:
        url_prefix = _join_paths(parent_prefix, blueprint.url_prefix)
        for route in blueprint.routes:
            endpoint = (
                f"{endpoint_prefix}.{route['endpoint']}"
                if endpoint_prefix
                else route["endpoint"]
            )
            self._add_route(
                _join_paths(url_prefix, route["rule"]),
                route["methods"],
                endpoint,
                route["func"],
            )
        for child in blueprint.blueprints:
            child_endpoint = (
                f"{endpoint_prefix}.{child.name}" if endpoint_prefix else child.name
            )
            self._register_blueprint(child, url_prefix, child_endpoint)

    def _add_route(
        self, rule: str, methods: list[str], endpoint: str, func: Callable
    ) -> None:
        starlette_path, params = _flask_path_to_starlette(rule)
        self._routes[endpoint] = starlette_path
        self._route_params[endpoint] = params
        self.fastapi_app.router.add_route(
            starlette_path,
            self._make_endpoint(func),
            methods=methods,
            name=endpoint,
        )

    def _make_endpoint(self, func: Callable) -> Callable:
        async def endpoint(starlette_request: StarletteRequest) -> Response:
            req = await _build_request(starlette_request)
            sid = starlette_request.cookies.get("session_id") or uuid.uuid4().hex
            sess = _sessions.setdefault(sid, {})
            app_token = _current_app.set(self)
            req_token = _current_request.set(req)
            g_token = _current_g.set(G())
            session_token = _current_session.set(sess)
            try:
                result = func(**starlette_request.path_params)
                if inspect.isawaitable(result):
                    result = await result
                response = _to_response(result)
                for handler in self._after_request:
                    response = handler(response)
                if "session_id" not in starlette_request.cookies:
                    response.set_cookie("session_id", sid, httponly=True)
                return response
            finally:
                _current_app.reset(app_token)
                _current_request.reset(req_token)
                _current_g.reset(g_token)
                _current_session.reset(session_token)

        return endpoint

    def after_request(self, func: Callable[[Response], Response]) -> Callable:
        self._after_request.append(func)
        return func

    def send_static_file(self, filename: str) -> FileResponse:
        return send_from_directory(self.static_folder, filename)

    def render_template(self, template_name: str, **context: Any) -> HTMLResponse:
        context.setdefault("g", g)
        html = self._jinja_env.get_template(template_name).render(**context)
        return HTMLResponse(html)

    def run(
        self,
        host: str | None = None,
        port: int | None = None,
        ssl_context: Any = None,
        **kwargs: Any,
    ) -> None:
        import uvicorn

        ssl_keyfile = ssl_certfile = None
        if ssl_context:
            ssl_certfile, ssl_keyfile = ssl_context
        uvicorn.run(
            self.fastapi_app,
            host=host or "127.0.0.1",
            port=port or 8000,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            **kwargs,
        )


def _join_paths(prefix: str, path: str) -> str:
    if not prefix:
        return path or "/"
    if not path or path == "/":
        return prefix
    return f"{prefix.rstrip('/')}/{path.lstrip('/')}"


async def _build_request(starlette_request: StarletteRequest) -> RequestShim:
    body = await starlette_request.body()
    form = MultiDict()
    files = MultiDict()
    content_type = starlette_request.headers.get("content-type", "")
    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form_data = await starlette_request.form()
        for key, value in form_data.multi_items():
            if hasattr(value, "filename") and hasattr(value, "read"):
                files.add(key, FileStorageShim(value.filename, await value.read()))
            else:
                form.add(key, value)

    json_data = None
    json_error = None
    if body and "application/json" in content_type:
        try:
            json_data = json.loads(body.decode() or "null")
        except json.JSONDecodeError as e:
            json_error = e

    return RequestShim(starlette_request, body, form, files, json_data, json_error)


def _to_response(result: Any) -> Response:
    status_code = None
    headers = None
    if isinstance(result, tuple):
        result, status_code, *rest = result
        if rest:
            headers = rest[0]
    if isinstance(result, Response):
        response = result
        if status_code is not None:
            response.status_code = status_code
    elif isinstance(result, (dict, list, BaseModel)):
        response = CompatJSONResponse(_dump_jsonable(result), status_code=status_code or 200)
    elif isinstance(result, (bytes, bytearray)):
        response = Response(result, status_code=status_code or 200)
    else:
        response = PlainTextResponse(str(result), status_code=status_code or 200)
    if headers:
        for key, value in headers.items():
            response.headers[key] = value
    return response


def render_template(template_name: str, **context: Any) -> HTMLResponse:
    return current_app.render_template(template_name, **context)


def send_from_directory(
    directory: str,
    path: str,
    as_attachment: bool = False,
    conditional: bool = False,
) -> FileResponse:
    return FileResponse(
        os.path.join(directory, path),
        filename=os.path.basename(path) if as_attachment else None,
    )


def url_for(endpoint: str, **values: Any) -> str:
    app = current_app._get_current_object()
    external = bool(values.pop("_external", False))
    path_template = app._routes[endpoint]
    params = app._route_params.get(endpoint, [])
    path = path_template
    for name in params:
        value = values.pop(name)
        path = re.sub(r"\{" + re.escape(name) + r"(?::[^}]+)?\}", str(value), path)
    if values:
        path = f"{path}?{urlencode(values)}"
    if external:
        req = _current_request.get()
        if req is not None:
            base = f"{req._request.url.scheme}://{req.host}"
            return base + path
    return path
