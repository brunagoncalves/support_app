from http import HTTPStatus

from fastapi.testclient import TestClient

from chat_app.main import app


def test_home_app():
    client = TestClient(app)
    response = client.get('/')
    assert response.json() == {'message': 'Welcome to the Chat App!'}
    assert response.status_code == HTTPStatus.OK
