import uuid

from fastapi.routing import APIRoute

from flask import (
    G,
    _build_request,
    _current_g,
    _current_request,
    _current_session,
    _sessions,
)


class WebCompatRoute(APIRoute):
    def get_route_handler(self):
        original_handler = super().get_route_handler()

        async def handler(request):
            req = await _build_request(request)
            sid = request.cookies.get("session_id") or uuid.uuid4().hex
            sess = _sessions.setdefault(sid, {})
            req_token = _current_request.set(req)
            g_token = _current_g.set(G())
            session_token = _current_session.set(sess)
            try:
                response = await original_handler(request)
                if "session_id" not in request.cookies:
                    response.set_cookie("session_id", sid, httponly=True)
                return response
            finally:
                _current_request.reset(req_token)
                _current_g.reset(g_token)
                _current_session.reset(session_token)

        return handler
