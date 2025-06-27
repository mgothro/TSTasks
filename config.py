from celery import Celery, Task
from flask import Flask
import os

class FlaskTask(Task):
    def __call__(self, *args, **kwargs):
        with self.app.app_context():
            return self.run(*args, **kwargs)

    def __init__(self):
        self.app = None

def google_email(json):
    return json["email"]

def create_app():
    app = Flask(__name__)

    app.config.update(
        SECRET_KEY=os.urandom(24),
        CELERY_BROKER_URL='redis://localhost:6379/0',
        CELERY_RESULT_BACKEND='redis://localhost:6379/0',
        CELERY_INCLUDE = ['tasks'],
        OAUTH2_PROVIDERS={
            "google": {
                "client_id": os.environ.get("task.client_id"),
                "client_secret": os.environ.get("task.client_secret"),
                "authorize_url": "https://accounts.google.com/o/oauth2/auth",
                "token_url": "https://accounts.google.com/o/oauth2/token",
                "userinfo": {
                    "url": "https://www.googleapis.com/oauth2/v3/userinfo",
                    "email": google_email,
                },
                "scopes": ["https://www.googleapis.com/auth/userinfo.email"],
            },
        }
    )
    return app

def make_celery(app):
    celery = Celery(
        'server',
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL'],
        include=app.config['CELERY_INCLUDE'],
        task_serializer = 'json',
        result_serializer = 'json',
        accept_content = ['json'],
        timezone = 'UTC',
        enable_utc = True,
        broker_connection_retry_on_startup = True
    )
    celery.autodiscover_tasks()
    celery.Task.app = app
    return celery