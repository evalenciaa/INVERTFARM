import pymysql
import os
pymysql.install_as_MySQLdb()
from pathlib import Path
from celery.schedules import crontab
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ===== SEGURIDAD =====
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-clave-por-defecto-solo-desarrollo')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
AUTH_USER_MODEL = 'farmacia.UsuarioPersonalizado'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'farmacia',
    'enfermeria',
    'auditoria',
    'rest_framework',
    'rest_framework_simplejwt',
    'axes',
    'dbbackup',
] 

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),  # ✅ FALTABA CERRAR TUPLA
}  # ✅ FALTABA CERRAR DICCIONARIO

MIDDLEWARE = [  # ✅ FALTABA CORCHETE DE APERTURA
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'auditoria.middleware.AuditoriaMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'farmacia.middleware.NoCacheMiddleware',
    'axes.middleware.AxesMiddleware',
]

# ===== CONFIGURACIÓN DE SESIONES (SEGURIDAD) =====
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 3600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG

CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'

ROOT_URLCONF = 'inventfarm.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'inventfarm.wsgi.application'

# ===== DATABASE =====
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.mysql'),
        'NAME': os.getenv('DB_NAME', 'INVENTFARM'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'farmacia', 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

if not DEBUG:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# SEGURIDAD EN PRODUCCIÓN
'''if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    
    # CSRF para producción
    CSRF_TRUSTED_ORIGINS = [
        'https://tu-dominio.com',  # Cambiar por tu dominio
        'http://tu-ip-servidor',    # Cambiar por IP del servidor
    ]'''

# Logo para reportes
LOGO_REPORTES = os.path.join(BASE_DIR, 'farmacia/static/farmacia/img/logo.png')

# Authentication
LOGIN_REDIRECT_URL = 'principal'     
LOGIN_URL = 'login'                   
LOGOUT_REDIRECT_URL = 'login'         

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
]

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Celery
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_BEAT_SCHEDULE = {
    'verificar-alertas-cpm': {
        'task': 'farmacia.tasks.verificar_alertas_cpm',
        'schedule': crontab(hour=8, minute=0),
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ===== SEGURIDAD HTTP (ISO 27001 A.14.1.2 / OWASP) =====
SECURE_CONTENT_TYPE_NOSNIFF = True      # Evita MIME-type sniffing
X_FRAME_OPTIONS = 'DENY'               # Previene Clickjacking
SECURE_BROWSER_XSS_FILTER = True       # Activa filtro XSS del navegador (legacy)

# Límite de tamaño de subida de archivos: 5 MB máximo (previene DoS)
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ===== CONFIGURACIÓN DE DJANGO-AXES (RATE LIMITING) =====
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_ENABLED = True
AXES_CACHE = 'default'
AXES_LOCKOUT_TEMPLATE = None
AXES_VERBOSE = True
AXES_FAILURE_LIMIT_PER_IP = None
AXES_LOCK_OUT_AT_FAILURE = True


# ===== CONFIGURACIÓN DE BACKUPS =====
# Nota: No usamos django-dbbackup directamente, sino implementación custom

# Directorio donde se guardarán los backups
DBBACKUP_BACKUP_DIRECTORY = os.path.join(BASE_DIR, 'backups')
if not os.path.exists(DBBACKUP_BACKUP_DIRECTORY):
    os.makedirs(DBBACKUP_BACKUP_DIRECTORY)

DBBACKUP_CONNECTORS = {
    'default': {
        'CONNECTOR': 'dbbackup.db.mysql.MysqlDumpConnector',
    }
}

# Mantener los últimos 10 backups
DBBACKUP_CLEANUP_KEEP = 10
DBBACKUP_CLEANUP_KEEP_MEDIA = 10
DBBACKUP_FILENAME_TEMPLATE = 'backup_{datetime}.{extension}'
DBBACKUP_MEDIA_FILENAME_TEMPLATE = 'media_{datetime}.{extension}'
DBBACKUP_COMPRESS_FILE = True

# LOGGING (muy útil en producción)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django_errors.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Crear carpeta de logs si no existe
if not os.path.exists(os.path.join(BASE_DIR, 'logs')):
    os.makedirs(os.path.join(BASE_DIR, 'logs'))