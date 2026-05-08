import os
import sys
import unittest
import json
from pathlib import Path

from fastapi.testclient import TestClient


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
os.chdir(APP_DIR)

import main  # noqa: E402
from core.config_manager import Config  # noqa: E402
from server.native import require_game_user  # noqa: E402


class FastAPIMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Config.API_TOKEN = 'test-token'
        cls.client = TestClient(main.app.fastapi_app)

    def test_basic_game_routes(self):
        root = self.client.get('/')
        self.assertEqual(root.status_code, 200)
        self.assertEqual(root.text, 'Hello World!')

        game_info = self.client.get('/game/info')
        self.assertEqual(game_info.status_code, 200)
        self.assertTrue(game_info.json()['success'])
        self.assertIn('max_stamina', game_info.json()['value'])

        score_token = self.client.get('/score/token')
        self.assertEqual(score_token.status_code, 200)
        self.assertEqual(score_token.json()['value']['token'], '1145141919810')

    def test_compose_aggregate_awaits_native_handlers(self):
        main.app.fastapi_app.dependency_overrides[require_game_user] = lambda: 2000000
        self.addCleanup(main.app.fastapi_app.dependency_overrides.clear)

        calls = [
            {'endpoint': '/user/me', 'id': 0},
            {'endpoint': '/purchase/bundle/pack', 'id': 1},
            {'endpoint': '/serve/download/me/song?url=false', 'id': 2},
            {'endpoint': '/game/info', 'id': 3},
            {'endpoint': '/present/me?lang=zh-Hans', 'id': 4},
            {'endpoint': '/world/map/me', 'id': 5},
            {'endpoint': '/purchase/bundle/bundle', 'id': 6},
            {'endpoint': '/finale/progress', 'id': 7},
            {'endpoint': '/purchase/bundle/single', 'id': 8},
        ]
        response = self.client.get(
            '/steeptennis/40/compose/aggregate',
            params={'calls': json.dumps(calls)},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['success'])
        self.assertEqual([item['id'] for item in body['value']], list(range(9)))
        self.assertIn('max_stamina', body['value'][3]['value'])

    def test_web_login_session(self):
        login = self.client.post(
            '/web/login',
            data={'username': Config.USERNAME, 'password': Config.PASSWORD},
            follow_redirects=False,
        )
        self.assertEqual(login.status_code, 302)
        self.assertEqual(login.headers['location'], '/web/index')

        index = self.client.get('/web/index', follow_redirects=False)
        self.assertEqual(index.status_code, 200)
        self.assertIn(b'Arcaea Server', index.content)

    def test_api_auth_and_pydantic_json_validation(self):
        invalid_json = self.client.post(
            '/api/v1/users',
            content=b'{',
            headers={'content-type': 'application/json', 'Token': Config.API_TOKEN},
        )
        self.assertEqual(invalid_json.status_code, 400)
        self.assertEqual(invalid_json.json()['code'], -1)

        missing_required = self.client.post(
            '/api/v1/users',
            json={'name': 'alice'},
            headers={'Token': Config.API_TOKEN},
        )
        self.assertEqual(missing_required.status_code, 200)
        self.assertEqual(missing_required.json()['code'], -100)
        self.assertIn('Missing parameter', missing_required.json()['msg'])

        bad_patch = self.client.patch(
            '/api/v1/purchases/test/items',
            json={'create': 'not-a-list'},
            headers={'Token': Config.API_TOKEN},
        )
        self.assertEqual(bad_patch.status_code, 200)
        self.assertEqual(bad_patch.json()['code'], -100)
        self.assertIn('must be a list', bad_patch.json()['msg'])

        no_token = self.client.get('/api/v1/items')
        self.assertEqual(no_token.status_code, 401)
        self.assertEqual(no_token.json()['code'], -1)

        bad_item_update = self.client.put(
            '/api/v1/items/pack/not-real',
            json={'is_available': 'yes'},
            headers={'Token': Config.API_TOKEN},
        )
        self.assertEqual(bad_item_update.status_code, 200)
        self.assertEqual(bad_item_update.json()['code'], -101)

<<<<<<< HEAD
    def test_openapi_documents_security_responses_and_game_payloads(self):
        response = self.client.get('/openapi.json')
        self.assertEqual(response.status_code, 200)
        schema = response.json()

        security_schemes = schema['components']['securitySchemes']
        self.assertIn('APIKeyHeader', security_schemes)
        self.assertIn('HTTPBearer', security_schemes)

        api_users = schema['paths']['/api/v1/users']['get']
        self.assertEqual(api_users['security'], [{'APIKeyHeader': []}])
        self.assertIn('ApiSuccessResponse', api_users['responses']['200']['content']['application/json']['schema']['$ref'])

        game_user = schema['paths']['/steeptennis/40/user/me']['get']
        self.assertEqual(game_user['security'], [{'HTTPBearer': []}])
        self.assertIn('GameSuccessResponse', game_user['responses']['200']['content']['application/json']['schema']['$ref'])

        login_body = schema['paths']['/steeptennis/40/auth/login']['post']['requestBody']['content']
        self.assertIn('application/x-www-form-urlencoded', login_body)

        score_query_names = [
            param['name']
            for param in schema['paths']['/steeptennis/40/score/token/world']['get']['parameters']
        ]
        self.assertIn('song_id', score_query_names)
        self.assertIn('difficulty', score_query_names)

        multiplayer_body = schema['paths']['/steeptennis/40/multiplayer/me/room/create']['post']['requestBody']['content']
        self.assertIn('application/json', multiplayer_body)

=======
>>>>>>> 954947bebc112b062367f7d2cb788031ac3c0979

if __name__ == '__main__':
    unittest.main()
