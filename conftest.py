import pytest
from src.app import app





@pytest.fixture(scope='session')
def app():
    return app


@pytest.fixture(scope='function')
def client(app):
    with app.test_client() as client:
        yield client
