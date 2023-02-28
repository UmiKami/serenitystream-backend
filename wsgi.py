# This file was created to run the application on render.com using gunicorn.

from src.app import app as application

if __name__ == "__main__":
    application.run()
    