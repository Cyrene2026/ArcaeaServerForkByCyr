# encoding: utf-8

import os
from importlib import import_module

from core.config_manager import Config, ConfigManager

if os.path.exists('config.py') or os.path.exists('config'):
    # 导入用户自定义配置
    ConfigManager.load(import_module("config").Config)
    # TODO: More config file formats

import sys
from logging.config import dictConfig
from multiprocessing import Process, current_process, set_start_method
from traceback import format_exc

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse, Response
from flask import Flask

import api
import server
import web
# import webapi
from core.bundle import BundleDownload
from core.constant import Constant
from core.download import UserDownload
from core.error import ArcError, NoAccess, RateLimit
from core.init import FileChecker
from core.sql import Connect
from server.native import game_error

app = Flask(__name__)

if Config.USE_PROXY_FIX:
    # 代理修复
    pass
if Config.USE_CORS:
    # 服务端跨域
    app.fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


os.chdir(os.path.dirname(os.path.abspath(__file__)))  # 更改工作路径，以便于愉快使用相对路径


app.config.from_mapping(SECRET_KEY=Config.SECRET_KEY)
app.config['SESSION_TYPE'] = 'filesystem'
web.register_routers(app)
server.register_routers(app.fastapi_app)
api.register_routers(app.fastapi_app)
# webapi is superseded by api.register_routers().


@app.fastapi_app.get('/swagger', include_in_schema=False)
def swagger():
    return RedirectResponse('/docs')


@app.fastapi_app.get('/', response_class=PlainTextResponse)
def hello():
    return "Hello World!"


@app.fastapi_app.get('/favicon.ico')  # 图标
def favicon():
    # Pixiv ID: 82374369
    # 我觉得这张图虽然并不是那么精细，但很有感觉，色彩的强烈对比下给人带来一种惊艳
    # 然后在压缩之下什么也看不清了:(

    return FileResponse(os.path.join(app.static_folder, 'favicon.ico'))


@app.fastapi_app.get('/download/{file_path:path}', name='download')  # 下载
def download(file_path: str, request: Request):
    with Connect(in_memory=True) as c:
        try:
            x = UserDownload(c)
            x.token = request.query_params.get('t')
            x.song_id, x.file_name = file_path.split('/', 1)
            x.select_for_check()
            if x.is_limited:
                raise RateLimit(
                    f'User `{x.user.user_id}` has reached the download limit.', 903)
            if not x.is_valid:
                raise NoAccess('Expired token.')
            x.download_hit()
            if Config.DOWNLOAD_USE_NGINX_X_ACCEL_REDIRECT:
                # nginx X-Accel-Redirect
                response = Response()
                response.headers['Content-Type'] = 'application/octet-stream'
                response.headers['X-Accel-Redirect'] = Config.NGINX_X_ACCEL_REDIRECT_PREFIX + file_path
                return response
            return FileResponse(os.path.join(Constant.SONG_FILE_FOLDER_PATH, file_path), filename=os.path.basename(file_path))
        except ArcError as e:
            if Config.ALLOW_WARNING_LOG:
                app.logger.warning(format_exc())
            return game_error(e)
    return game_error()


@app.fastapi_app.get('/bundle_download/{token}', name='bundle_download')  # 热更新下载
def bundle_download(token: str, request: Request):
    with Connect(in_memory=True) as c_m:
        try:
            app.logger.info('[bundle_download] request start ip=%s token=%s...',
                            request.client.host if request.client else '', token[:12])
            file_path = BundleDownload(c_m).get_path_by_token(
                token, request.client.host if request.client else '')
            abs_path = os.path.join(
                Constant.CONTENT_BUNDLE_FOLDER_PATH, file_path)
            app.logger.info(
                '[bundle_download] resolved token=%s... file_path=%s abs_path=%s exists=%s',
                token[:12],
                file_path,
                abs_path,
                os.path.isfile(abs_path)
            )
            if Config.DOWNLOAD_USE_NGINX_X_ACCEL_REDIRECT:
                # nginx X-Accel-Redirect
                response = Response()
                response.headers['Content-Type'] = 'application/octet-stream'
                response.headers['X-Accel-Redirect'] = Config.BUNDLE_NGINX_X_ACCEL_REDIRECT_PREFIX + file_path
                app.logger.info(
                    '[bundle_download] response x_accel token=%s... redirect=%s',
                    token[:12],
                    response.headers['X-Accel-Redirect']
                )
                return response
            app.logger.info('[bundle_download] response send_file token=%s... file_path=%s',
                            token[:12], file_path)
            return FileResponse(os.path.join(Constant.CONTENT_BUNDLE_FOLDER_PATH, file_path), filename=os.path.basename(file_path))
        except ArcError as e:
            if Config.ALLOW_WARNING_LOG:
                app.logger.warning(format_exc())
            app.logger.warning(
                '[bundle_download] arc_error token=%s... status=%s error_code=%s message=%s',
                token[:12],
                e.status,
                e.error_code,
                e
            )
            return game_error(e)
        except Exception:
            app.logger.error(
                '[bundle_download] unhandled_error token=%s...\n%s',
                token[:12],
                format_exc()
            )
            raise
    return game_error()


app._routes['download'] = '/download/{file_path:path}'
app._route_params['download'] = ['file_path']
app._routes['bundle_download'] = '/bundle_download/{token}'
app._route_params['bundle_download'] = ['token']


if Config.DEPLOY_MODE == 'waitress':
    # 给waitress加个日志
    @app.fastapi_app.middleware('http')
    async def after_request(request: Request, call_next):
        response = await call_next(request)
        client_host = request.client.host if request.client else ''
        app.logger.info(
            f'{client_host} - - {request.method} {request.url.path} {response.status_code}')
        return response

# @app.before_request
# def before_request():
#     print(request.path)
#     print(request.headers)
#     print(request.data)


def tcp_server_run():
    import uvicorn

    app.logger.info(
        'Running FastAPI ASGI server... (%s:%s, deploy_mode=%s)',
        Config.HOST,
        Config.PORT,
        Config.DEPLOY_MODE,
    )
    uvicorn.run(
        app.fastapi_app,
        host=Config.HOST,
        port=Config.PORT,
        ssl_certfile=Config.SSL_CERT or None,
        ssl_keyfile=Config.SSL_KEY or None,
        proxy_headers=Config.USE_PROXY_FIX,
    )


def generate_log_file_dict(level: str, filename: str) -> dict:
    return {
        "class": "logging.handlers.RotatingFileHandler",
        "maxBytes": 1024 * 1024,
        "backupCount": 1,
        "encoding": "utf-8",
        "level": level,
        "formatter": "default",
        "filename": filename
    }


def pre_main():
    log_dict = {
        'version': 1,
        'root': {
            'level': 'INFO',
            'handlers': ['wsgi', 'error_file']
        },
        'handlers': {
            'wsgi': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stderr',
                'formatter': 'default'
            },
            "error_file": generate_log_file_dict('ERROR', f'{Config.LOG_FOLDER_PATH}/error.log')
        },
        'formatters': {
            'default': {
                'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
            }
        }
    }
    if Config.ALLOW_INFO_LOG:
        log_dict['root']['handlers'].append('info_file')
        log_dict['handlers']['info_file'] = generate_log_file_dict(
            'INFO', f'{Config.LOG_FOLDER_PATH}/info.log')
    if Config.ALLOW_WARNING_LOG:
        log_dict['root']['handlers'].append('warning_file')
        log_dict['handlers']['warning_file'] = generate_log_file_dict(
            'WARNING', f'{Config.LOG_FOLDER_PATH}/warning.log')

    dictConfig(log_dict)

    Connect.logger = app.logger
    if not FileChecker(app.logger).check_before_run():
        app.logger.error('Some errors occurred. The server will not run.')
        input('Press ENTER key to exit.')
        sys.exit()


def main():
    if Config.LINKPLAY_HOST and Config.SET_LINKPLAY_SERVER_AS_SUB_PROCESS:
        from linkplay_server import link_play
        process = [Process(target=link_play, args=(
            Config.LINKPLAY_HOST, int(Config.LINKPLAY_UDP_PORT), int(Config.LINKPLAY_TCP_PORT)))]
        [p.start() for p in process]
        app.logger.info(
            f"Link Play UDP server is running on {Config.LINKPLAY_HOST}:{Config.LINKPLAY_UDP_PORT} ...")
        app.logger.info(
            f"Link Play TCP server is running on {Config.LINKPLAY_HOST}:{Config.LINKPLAY_TCP_PORT} ...")
        tcp_server_run()
        [p.join() for p in process]
    else:
        tcp_server_run()


# must run for init
# this ensures avoiding duplicate init logs for some reason
if current_process().name == 'MainProcess':
    pre_main()

if __name__ == '__main__':
    set_start_method("spawn")
    main()


# Made By Lost  2020.9.11
