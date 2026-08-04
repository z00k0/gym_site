from .settings import *  # noqa: F403
from .settings import MIDDLEWARE as BASE_MIDDLEWARE

MIDDLEWARE = [
    item for item in BASE_MIDDLEWARE if item != "whitenoise.middleware.WhiteNoiseMiddleware"
]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
