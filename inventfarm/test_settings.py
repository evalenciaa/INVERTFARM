import os

from .settings import *  # noqa: F403


# La suite usa SQLite por defecto. Para comprobar el comportamiento real de
# bloqueos y transacciones, activar INVENTFARM_TEST_MYSQL=True y conservar la
# ejecución con --keepdb. El nombre de prueba jamás apunta a INVENTFARM.
if os.getenv('INVENTFARM_TEST_MYSQL', 'False').lower() == 'true':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('DB_NAME', 'INVENTFARM'),
            'USER': os.getenv('TEST_DB_USER', os.getenv('DB_USER', '')),
            'PASSWORD': os.getenv('TEST_DB_PASSWORD', os.getenv('DB_PASSWORD', '')),
            'HOST': os.getenv('TEST_DB_HOST', os.getenv('DB_HOST', 'localhost')),
            'PORT': os.getenv('TEST_DB_PORT', os.getenv('DB_PORT', '3306')),
            'OPTIONS': {'charset': 'utf8mb4'},
            'TEST': {'NAME': os.getenv('TEST_DB_NAME', 'inventfarm_test')},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
CELERY_TASK_ALWAYS_EAGER = True
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
AXES_ENABLED = False
