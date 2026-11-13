"""Tests that reproduce the previously unhandled Ollama JSON parse failure."""
import pytest
from src import vlm


class MockResponse:
    def __init__(self, content, *, json_error=False, status_code=200, done_reason='stop'):
        self.content = content
        self.json_error = json_error
        self.status_code = status_code
        self.headers = {'content-type': 'application/json' if not json_error else 'text/html'}
        self.done_reason = done_reason

    def raise_for_status(self):
        pass

    def json(self):
        if self.json_error:
            raise ValueError('Expecting value: line 1 column 1 (char 0)')
        return {'message': {'content': self.content}, 'done_reason': self.done_reason}


def test_ollama_json_envelope_is_decoded(monkeypatch):
    calls = []
    def post(url, json, timeout):
        calls.append(json)
        return MockResponse('{"scene_summary": "a cup", "objects": []}')
    monkeypatch.setattr(vlm.requests, 'post', post)
    result = vlm._chat([{'role': 'user', 'content': 'Describe'}])
    assert result['scene_summary'] == 'a cup'
    assert calls[0]['format'] == 'json'
    assert calls[0]['stream'] is False


def test_empty_content_retries_without_json_mode(monkeypatch):
    calls = []
    responses = [MockResponse(''), MockResponse('```json\n{"scene_summary":"a cup","objects":[]}\n```')]
    def post(url, json, timeout):
        calls.append(json)
        return responses.pop(0)
    monkeypatch.setattr(vlm.requests, 'post', post)
    assert vlm._chat([{'role':'user','content':'Describe'}])['scene_summary'] == 'a cup'
    assert calls[0]['format'] == 'json'
    assert 'format' not in calls[1]


def test_non_json_http_response_has_clear_message(monkeypatch):
    monkeypatch.setattr(vlm.requests, 'post', lambda *a, **k: MockResponse('', json_error=True))
    with pytest.raises(vlm.VLMResponseError, match='non-JSON HTTP response'):
        vlm._chat([{'role':'user','content':'Describe'}])


def test_repeated_empty_content_has_clear_message(monkeypatch):
    monkeypatch.setattr(vlm.requests, 'post', lambda *a, **k: MockResponse('', done_reason='length'))
    with pytest.raises(vlm.VLMResponseError, match='empty answer'):
        vlm._chat([{'role':'user','content':'Describe'}])


def test_invalid_model_json_does_not_silently_succeed(monkeypatch):
    monkeypatch.setattr(vlm.requests, 'post', lambda *a, **k: MockResponse('This is not JSON'))
    with pytest.raises(vlm.VLMResponseError, match='instead of JSON'):
        vlm._chat([{'role':'user','content':'Describe'}])


def test_plain_text_with_json_object_is_parsed():
    assert vlm._extract_json_object('JSON follows: {"ok": true}') == {'ok': True}
