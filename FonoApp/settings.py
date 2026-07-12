from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-)dj+y&$f2+q)elr0c!&k2fo^*^y+l$p*&l+civ#k3)fx959a0%'

RECAPTCHA_SECRET_KEY = '6LfRpCUtAAAAACCBt7qHtR_2WYPGjM3mcoQUwrku'

DEBUG = True

ALLOWED_HOSTS = []

DEV_APPS = [
    'FonoAppAdministracion',
    'FonoAppCuidados',
    'FonoAppDiagnostico',
    'FonoAppInformacion',
    'FonoAppNoticias',
]

BASE_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

FRAMEWORKS = [
    'rest_framework',
    'corsheaders',
    'rest_framework_simplejwt'
]

INSTALLED_APPS = DEV_APPS + BASE_APPS + FRAMEWORKS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
]

ROOT_URLCONF = 'FonoApp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'FonoApp.wsgi.application'


# Dev db
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql', # Motor de base de datos
        'NAME': 'fonoDevDB',                 # Nombre de tu base de datos PostgreSQL
        'USER': 'admin',                   # Usuario de PostgreSQL
        'PASSWORD': 'secret',            # Contraseña del usuario
        'HOST': 'localhost',                       # O la IP/dominio de tu servidor DB
        'PORT': '5432',                            # Puerto por defecto de PostgreSQL
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'FonoAppFunciones.authentication.CustomJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

AUTH_USER_MODEL = 'FonoAppAdministracion.FonoApp_Administracion' # Formato: 'nombre_app.NombreModelo'

# JWT config
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
    
    # AGREGA ESTA LÍNEA:
    'USER_ID_FIELD': 'id_usuario',  # Aquí le decimos que use tu campo personalizado
    'USER_ID_CLAIM': 'user_id',    # Este es el nombre que tendrá dentro del token JSON
}

"""
    MANEJO DE IMAGENES
"""

import os

# Carpeta física donde se guardan los archivos
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# URL base desde la cual se servirán en el navegador
MEDIA_URL = '/media/'