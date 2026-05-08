import json
import os
from functools import lru_cache
from time import time

from flask import current_app, has_app_context, url_for

from .config_manager import Config
from .constant import Constant
from .error import NoAccess, NoData, RateLimit
from .limiter import ArcLimiter


def bundle_trace(trace_id: str, message: str, *args) -> None:
    if has_app_context():
        current_app.logger.info('[content_bundle:%s] ' + message,
                                trace_id or '-', *args)


def bundle_download_trace(message: str, *args) -> None:
    if has_app_context():
        current_app.logger.info('[bundle_download] ' + message, *args)


class ContentBundle:

    def __init__(self) -> None:
        self.version: str = None
        self.prev_version: str = None
        self.app_version: str = None
        self.uuid: str = None

        self.json_size: int = None
        self.bundle_size: int = None
        self.json_path: str = None  # relative path
        self.bundle_path: str = None  # relative path
        self.bundle_sizes: 'list[int]' = []
        self.bundle_paths: 'list[str]' = []

        self.json_url: str = None
        self.bundle_url: str = None
        self.bundle_urls: 'list[str]' = []

    @staticmethod
    def parse_version(version: str) -> tuple:
        try:
            r = tuple(map(int, version.split('.')))
        except AttributeError:
            r = (0, 0, 0)
        return r

    @property
    def version_tuple(self) -> tuple:
        return self.parse_version(self.version)

    @classmethod
    def from_json(cls, json_data: dict) -> 'ContentBundle':
        x = cls()
        x.version = json_data['versionNumber']
        x.prev_version = json_data['previousVersionNumber']
        x.app_version = json_data['applicationVersionNumber']
        x.uuid = json_data['uuid']
        if x.prev_version is None:
            x.prev_version = '0.0.0'
        return x

    def to_dict(self) -> dict:
        r = {
            'contentBundleVersion': self.version,
            'appVersion': self.app_version,
            'jsonSize': self.json_size,
            'bundleParts': [{'bundleSize': x} for x in self.bundle_sizes]
        }
        if self.json_url and self.bundle_urls:
            r['jsonUrl'] = self.json_url
            for index, url in enumerate(self.bundle_urls):
                r['bundleParts'][index]['bundleUrl'] = url
        return r

    def calculate_size(self) -> None:
        self.json_size = os.path.getsize(os.path.join(
            Constant.CONTENT_BUNDLE_FOLDER_PATH, self.json_path))
        self.bundle_sizes = [
            os.path.getsize(os.path.join(
                Constant.CONTENT_BUNDLE_FOLDER_PATH, x))
            for x in self.bundle_paths
        ]
        self.bundle_size = sum(self.bundle_sizes)


class BundleParser:

    # {app_version: [ List[ContentBundle] ]}
    bundles: 'dict[str, list[ContentBundle]]' = {}
    # {app_version: max bundle version}
    max_bundle_version: 'dict[str, str]' = {}

    # {bundle version: [next versions]} 宽搜索引
    next_versions: 'dict[str, list[str]]' = {}
    # {(bver, b prev version): ContentBundle} 正向索引
    version_tuple_bundles: 'dict[tuple[str, str], ContentBundle]' = {}

    def __init__(self) -> None:
        if not self.bundles:
            self.parse()

    @staticmethod
    def get_bundle_part_paths(root: str, file_stem: str, total_partitions: int) -> 'list[str]':
        if total_partitions <= 1:
            return [os.path.join(root, f'{file_stem}.cb')]

        part_paths = []
        for i in range(total_partitions):
            candidates = [
                os.path.join(root, f'{file_stem}.part{i}.cb'),
                os.path.join(root, f'{file_stem}_{i}.cb')
            ]
            for candidate in candidates:
                if os.path.isfile(candidate):
                    part_paths.append(candidate)
                    break
            else:
                raise FileNotFoundError(
                    f'Bundle part file not found: {candidates}')
        return part_paths

    def re_init(self) -> None:
        self.bundles.clear()
        self.max_bundle_version.clear()
        self.next_versions.clear()
        self.version_tuple_bundles.clear()
        self.get_bundles.cache_clear()
        self.parse()

    def parse(self) -> None:
        for root, dirs, files in os.walk(Constant.CONTENT_BUNDLE_FOLDER_PATH):
            for file in files:
                if not file.endswith('.json'):
                    continue

                json_path = os.path.join(root, file)
                with open(json_path, 'rb') as f:
                    data = json.load(f)

                x = ContentBundle.from_json(data)
                total_partitions = data.get('totalPartitions', 1)
                bundle_paths = self.get_bundle_part_paths(
                    root, file[:-5], total_partitions)

                x.json_path = os.path.relpath(
                    json_path, Constant.CONTENT_BUNDLE_FOLDER_PATH)
                x.bundle_paths = [
                    os.path.relpath(i, Constant.CONTENT_BUNDLE_FOLDER_PATH)
                    for i in bundle_paths
                ]
                x.bundle_path = x.bundle_paths[0]

                x.json_path = x.json_path.replace('\\', '/')
                x.bundle_paths = [i.replace('\\', '/') for i in x.bundle_paths]
                x.bundle_path = x.bundle_paths[0]

                for i in bundle_paths:
                    if not os.path.isfile(i):
                        raise FileNotFoundError(
                            f'Bundle file not found: {i}')
                x.calculate_size()

                self.bundles.setdefault(x.app_version, []).append(x)

                self.version_tuple_bundles[(x.version, x.prev_version)] = x
                self.next_versions.setdefault(
                    x.prev_version, []).append(x.version)

        # sort by version
        for k, v in self.bundles.items():
            v.sort(key=lambda x: x.version_tuple)
            self.max_bundle_version[k] = v[-1].version

    @staticmethod
    @lru_cache(maxsize=Constant.LRU_CACHE_MAX_SIZE['get_bundles'])
    def get_bundles(app_ver: str, b_ver: str) -> 'list[ContentBundle]':
        if Config.BUNDLE_STRICT_MODE:
            return BundleParser.bundles.get(app_ver, [])

        k = b_ver if b_ver else '0.0.0'

        target_version = BundleParser.max_bundle_version.get(app_ver, '0.0.0')
        if k == target_version:
            return []

        # BFS
        q = [[k]]
        ans = None
        while True:
            qq = []
            for x in q:
                if x[-1] == target_version:
                    ans = x
                    break
                for y in BundleParser.next_versions.get(x[-1], []):
                    if y in x:
                        continue
                    qq.append(x + [y])

            if ans is not None or not qq:
                break
            q = qq

        if not ans:
            raise NoData(
                f'No bundles found for app version: {app_ver}, bundle version: {b_ver}', status=404)

        r = []
        for i in range(1, len(ans)):
            r.append(BundleParser.version_tuple_bundles[(ans[i], ans[i-1])])

        return r


class BundleDownload:

    limiter = ArcLimiter(
        Constant.BUNDLE_DOWNLOAD_TIMES_LIMIT, 'bundle_download')

    def __init__(self, c_m=None, trace_id: str = None):
        self.c_m = c_m
        self.trace_id = trace_id

        self.client_app_version = None
        self.client_bundle_version = None
        self.device_id = None

    def set_client_info(self, app_version: str, bundle_version: str, device_id: str = None) -> None:
        self.client_app_version = app_version
        self.client_bundle_version = bundle_version
        self.device_id = device_id
        bundle_trace(
            self.trace_id,
            'client_info app_version=%s content_bundle=%s device_id=%s',
            app_version,
            bundle_version,
            device_id
        )

    def get_bundle_list(self) -> list:
        target_version = BundleParser.max_bundle_version.get(
            self.client_app_version, '0.0.0')
        available_versions = [
            x.version for x in BundleParser.bundles.get(self.client_app_version, [])]
        bundle_trace(
            self.trace_id,
            'select start strict_mode=%s app_version=%s client_bundle=%s target_bundle=%s available_versions=%s',
            Config.BUNDLE_STRICT_MODE,
            self.client_app_version,
            self.client_bundle_version,
            target_version,
            available_versions
        )
        try:
            bundles: 'list[ContentBundle]' = BundleParser.get_bundles(
                self.client_app_version, self.client_bundle_version)
        except Exception:
            bundle_trace(
                self.trace_id,
                'select failed app_version=%s client_bundle=%s target_bundle=%s',
                self.client_app_version,
                self.client_bundle_version,
                target_version
            )
            raise

        bundle_trace(
            self.trace_id,
            'select done bundle_count=%s selected=%s',
            len(bundles),
            [(x.prev_version, x.version, x.json_path, x.bundle_path)
             for x in bundles]
        )

        if not bundles:
            bundle_trace(self.trace_id, 'no update needed')
            return []

        now = time()

        if Constant.BUNDLE_DOWNLOAD_LINK_PREFIX:
            prefix = Constant.BUNDLE_DOWNLOAD_LINK_PREFIX
            if prefix[-1] != '/':
                prefix += '/'

            def url_func(x): return f'{prefix}{x}'
            bundle_trace(self.trace_id, 'url mode=config prefix=%s', prefix)
        else:
            def url_func(x): return url_for(
                'bundle_download', token=x, _external=True)
            bundle_trace(self.trace_id, 'url mode=url_for endpoint=bundle_download')

        sql_list = []
        r = []
        for x in bundles:
            if x.version_tuple <= ContentBundle.parse_version(self.client_bundle_version):
                bundle_trace(
                    self.trace_id,
                    'skip selected bundle version=%s client_bundle=%s',
                    x.version,
                    self.client_bundle_version
                )
                continue
            t1 = os.urandom(64).hex()

            x.json_url = url_func(t1)
            x.bundle_urls = []

            sql_list.append((t1, x.json_path, now, self.device_id))
            bundle_tokens = []
            for bundle_path in x.bundle_paths:
                token = os.urandom(64).hex()
                x.bundle_urls.append(url_func(token))
                sql_list.append((token, bundle_path, now, self.device_id))
                bundle_tokens.append(token)
            x.bundle_url = x.bundle_urls[0] if x.bundle_urls else None
            r.append(x.to_dict())
            bundle_trace(
                self.trace_id,
                'token generated version=%s json_path=%s json_size=%s json_token=%s... bundle_paths=%s bundle_sizes=%s bundle_tokens=%s',
                x.version,
                x.json_path,
                x.json_size,
                t1[:12],
                x.bundle_paths,
                x.bundle_sizes,
                [i[:12] + '...' for i in bundle_tokens]
            )

        if not sql_list:
            bundle_trace(self.trace_id, 'no token generated after filtering')
            return []

        self.clear_expired_token()

        self.c_m.executemany(
            '''insert into bundle_download_token values (?, ?, ?, ?)''', sql_list)
        bundle_trace(
            self.trace_id,
            'tokens inserted token_count=%s result_count=%s device_id=%s',
            len(sql_list),
            len(r),
            self.device_id
        )

        return r

    def get_path_by_token(self, token: str, ip: str) -> str:
        bundle_download_trace('lookup start ip=%s token=%s...', ip, token[:12])
        r = self.c_m.execute(
            '''select file_path, time, device_id from bundle_download_token where token = ?''', (token,)).fetchone()
        if not r:
            bundle_download_trace('lookup failed invalid_token ip=%s token=%s...', ip, token[:12])
            raise NoAccess('Invalid token.', status=403)
        file_path, create_time, device_id = r

        if time() - create_time > Constant.BUNDLE_DOWNLOAD_TIME_GAP_LIMIT:
            bundle_download_trace(
                'lookup failed expired ip=%s token=%s... file_path=%s age_seconds=%.2f device_id=%s',
                ip,
                token[:12],
                file_path,
                time() - create_time,
                device_id
            )
            raise NoAccess('Expired token.', status=403)

        if file_path.endswith('.cb') and not self.limiter.hit(ip):
            bundle_download_trace(
                'lookup failed rate_limited ip=%s token=%s... file_path=%s device_id=%s',
                ip,
                token[:12],
                file_path,
                device_id
            )
            raise RateLimit(
                f'Too many content bundle downloads, IP: {ip}, DeviceID: {device_id}', status=429)

        bundle_download_trace(
            'lookup done ip=%s token=%s... file_path=%s age_seconds=%.2f device_id=%s',
            ip,
            token[:12],
            file_path,
            time() - create_time,
            device_id
        )
        return file_path

    def clear_expired_token(self) -> None:
        self.c_m.execute(
            '''delete from bundle_download_token where time < ?''', (int(time() - Constant.BUNDLE_DOWNLOAD_TIME_GAP_LIMIT),))
        bundle_trace(
            self.trace_id,
            'expired tokens cleared older_than_seconds=%s',
            Constant.BUNDLE_DOWNLOAD_TIME_GAP_LIMIT
        )
