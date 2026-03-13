from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_samples() -> None:
    response = client.get('/samples')
    assert response.status_code == 200
    body = response.json()
    assert 'items' in body
    assert len(body['items']) >= 3
