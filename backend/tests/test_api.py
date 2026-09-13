import io
import secrets
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from fastapi.testclient import TestClient
from PIL import Image

from backend.config import Settings
from backend.main import create_app
from backend.mock import MockProvider
from backend.models import now


def key():
    return {'Idempotency-Key': secrets.token_hex(32)}


def photo():
    out = io.BytesIO()
    Image.new('RGB', (20, 20), 'white').save(out, format='PNG')
    return out.getvalue()


def setup(provider=None):
    app = create_app(Settings(ai_provider='mock'), provider)
    client = TestClient(app)
    headers = key()
    response = client.post('/api/v1/analyses', files={'photo': ('menu.png', photo(), 'image/png')}, headers=headers)
    assert response.status_code == 202, response.text
    accepted = response.json()
    path = '/api/v1/analyses/' + accepted['analysis_id']
    auth = {'Authorization': 'Bearer ' + accepted['session_token']}
    return app, client, path, auth, headers


def finish(client, path, auth):
    for _ in range(12):
        state = client.get(path, headers=auth).json()
        if not state['remaining_work']:
            return state
        response = client.post(path + '/continue', json={'state_version': state['state_version']}, headers=auth | key())
        assert response.status_code == 200, response.text
    raise AssertionError('did not terminate')


def test_full_flow_contract_and_isolation():
    app, client, path, auth, initial_key = setup()
    retry = client.post('/api/v1/analyses', files={'photo': ('menu.png', photo(), 'image/png')}, headers=initial_key)
    assert retry.json()['analysis_id'] == path.split('/')[-1]
    assert client.get(path).status_code == 401
    assert client.get(path, headers={'Authorization': 'Bearer wrong'}).status_code == 404
    state = finish(client, path, auth)
    assert state['status'] == 'done' and len(state['items']) == 2
    request_key = key()
    body = {'content': '그 음식은 어떻게 조리해?'}
    sent = client.post(path + '/messages', json=body, headers=auth | request_key)
    assert sent.status_code == 202
    assert client.post(path + '/messages', json=body, headers=auth | request_key).json() == sent.json()
    assert client.post(path + '/messages', json={'content': '다른 질문'}, headers=auth | request_key).status_code == 409
    state = finish(client, path, auth)
    assert '어떤 음식' in state['messages'][-1]['content']
    item = state['items'][0]
    edit_path = path + '/items/' + item['item_id']
    body = {'original_name': '醤油ラーメン', 'item_version': 1}
    edited = client.patch(edit_path, json=body, headers=auth | key())
    assert edited.status_code == 202
    assert edited.json()['items'][0]['citations'] == []
    assert client.patch(edit_path, json=body, headers=auth | key()).status_code == 409
    assert finish(client, path, auth)['items'][0]['item_version'] == 2
    assert client.delete(path, headers=auth).status_code == 204
    assert client.get(path, headers=auth).status_code == 404
    assert not app.state.store.sessions and not app.state.store.initial


def test_invalid_files_and_common_errors():
    client = TestClient(create_app(Settings(ai_provider='mock')))
    for data, mime, status in [(b'not png', 'image/png', 422), (b'x', 'image/gif', 415), (b'x' * 3145729, 'image/png', 413)]:
        response = client.post('/api/v1/analyses', files={'photo': ('x', data, mime)}, headers=key())
        assert response.status_code == status
        assert 'error' in response.json() and 'request_id' in response.json()
    assert client.get('/api/v1/analyses/not-a-uuid').status_code == 422


def test_expiry_and_version():
    app, client, path, auth, _ = setup()
    response = client.post(path + '/continue', json={'state_version': 900}, headers=auth | key())
    assert response.status_code == 409
    app.state.store.sessions[path.split('/')[-1]].expires_at = now() - timedelta(seconds=1)
    assert client.get(path, headers=auth).status_code == 404


def test_continue_after_completion_is_a_no_op():
    _, client, path, auth, _ = setup()
    state = finish(client, path, auth)
    response = client.post(path + '/continue', json={'state_version': state['state_version']}, headers=auth | key())
    assert response.status_code == 200, response.text
    assert response.json()['state_version'] == state['state_version']


def test_partial_failure_preserves_success():
    class Broken(MockProvider):
        def images(self, item, charge):
            if item.original_name == '焼き鳥':
                raise RuntimeError('secret upstream error')
            return super().images(item, charge)
    _, client, path, auth, _ = setup(Broken())
    state = finish(client, path, auth)
    assert [i['status'] for i in state['items']] == ['done', 'failed']
    assert 'secret' not in str(state)


def test_delete_during_execution_cannot_resurrect():
    entered, release = Event(), Event()
    class Slow(MockProvider):
        def extract(self, image, mime, charge):
            entered.set()
            release.wait(5)
            return super().extract(image, mime, charge)
    app, client, path, auth, _ = setup(Slow())
    client.post(path + '/continue', json={'state_version': 1}, headers=auth | key())
    with ThreadPoolExecutor() as pool:
        job = pool.submit(client.post, path + '/continue', json={'state_version': 2}, headers=auth | key())
        assert entered.wait(5)
        assert client.delete(path, headers=auth).status_code == 204
        release.set()
        assert job.result().status_code == 404
    assert not app.state.store.sessions
