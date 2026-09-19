import socket
from .settings import *

# Check if PostgreSQL is reachable; fallback to in-memory SQLite if not (e.g. when Docker is stopped)
_host = DATABASES["default"].get("HOST", "127.0.0.1")
_port = int(DATABASES["default"].get("PORT", 5432))
_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
_sock.settimeout(1.0)
_result = _sock.connect_ex((_host, _port))
_sock.close()

if _result != 0:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

# Check if Redis is reachable; fallback to LocMemCache if not (e.g. when Docker is stopped)
_redis_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
_redis_sock.settimeout(1.0)
_redis_res = _redis_sock.connect_ex(("127.0.0.1", 6379))
_redis_sock.close()

if _redis_res != 0:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
