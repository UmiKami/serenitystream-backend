import json
from src.app import app
from flask.testing import FlaskClient

BASELINE = "/api/v2"

class MyTestClient(FlaskClient):
    def open(self, *args, **kwargs):
        # Add the prefix to the URL before passing it to Flask's open method
        if 'url' in kwargs:
            kwargs['url'] = BASELINE + kwargs['url']
        else:
            args = list(args)
            args[0] = BASELINE + args[0]
            args = tuple(args)
        return super().open(*args, **kwargs)


app.test_client_class = MyTestClient
client = app.test_client()

def test_home():
    with client:
        response = client.get('/')
        assert response.status_code == 200
        assert response.data == b'Peace sweet peace! <strong> Your Yoga API! <strong>'
