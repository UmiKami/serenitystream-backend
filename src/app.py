# Imports necessary libraries
import os
from flask import Flask
from flask_cors import CORS
from src.routes import api
from flask_swagger_ui import get_swaggerui_blueprint

# flask app setup

app = Flask(__name__) # initializes flask application
app.url_map.strict_slashes = False # doesn't require a slash at the end of the URL

app.register_blueprint(api, url_prefix="/api/v2") # actually apply the prefix to the bp

SWAGGER_URL = '/api/v2/docs'  # URL for exposing Swagger UI (without trailing '/')
API_URL = '/static/swagger.json'  # Our API url (can of course be a local resource)

# Create swagger ui
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,  # Swagger UI static files will be mapped to '{SWAGGER_URL}/dist/'
    API_URL,
    config={  # Swagger UI config overrides
        'app_name': "Test application"
    }
)

app.register_blueprint(swaggerui_blueprint)

CORS(app, resources={r"*": {"origins": "*"}}) # prevents most CORS issues


# If the file is run directly,start the app.
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)

# To execute, run the file. Then go to 127.0.0.1:5000 in your browser and look at a welcoming message.