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
DEBUG = os.getenv('DEBUG', 'False') == 'True'
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
    'rest_framework',
    'rest_framework_simplejwt',
    'axes',
]  # ✅ FALTABA CERRAR AQUÍ

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
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'INVENTFARM'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
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

# Media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

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
