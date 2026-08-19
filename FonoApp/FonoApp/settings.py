import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga variables desde FonoApp/.env (no sobreescribe variables ya definidas en el entorno real,
# por lo que en producción basta con exportar las variables del sistema/proveedor de hosting).
load_dotenv(BASE_DIR / '.env')


def env_bool(nombre, default=False):
    """Convierte el valor de una variable de entorno tipo 'true'/'false' a booleano."""
    return os.environ.get(nombre, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(nombre, default=''):
    """Convierte una variable de entorno separada por comas en una lista de strings."""
    valor = os.environ.get(nombre, default)
    return [item.strip() for item in valor.split(',') if item.strip()]


SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-)dj+y&$f2+q)elr0c!&k2fo^*^y+l$p*&l+civ#k3)fx959a0%'
)

RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY', '')

DEBUG = env_bool('DEBUG', True)

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')

DEV_APPS = [
    'FonoAppAdministracion',
    'FonoAppCuidados',
    'FonoAppDiagnostico',
    'FonoAppInformacion',
    'FonoAppNoticias',
    'FonoAppInfoGeneral',
    'FonoAppVoz',
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

CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS', 'http://localhost:4200')

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


# Base de datos:
# - En desarrollo se arma con las variables DB_* (ver .env / .env.example, coinciden con docker-compose.yml).
# - En despliegue, si se define DATABASE_URL (formato estándar de 12-factor: postgres://user:pass@host:port/nombre),
#   esta tiene prioridad sobre las variables DB_* (ver .env.production.example).
# Motor de base de datos: 'postgresql' (default, igual que siempre) o 'mysql'
# (usado en el despliegue en cPanel, ver deploy/mysql/). Definir DB_ENGINE=mysql
# solo afecta al camino DB_* de abajo; con DATABASE_URL el motor se detecta
# solo por el esquema de la URL ("postgres://" o "mysql://").
DB_ENGINE = os.environ.get('DB_ENGINE', 'postgresql').strip().lower()

_ENGINES = {
    'postgresql': 'django.db.backends.postgresql',
    'mysql': 'django.db.backends.mysql',
}

if os.environ.get('DATABASE_URL'):
    import dj_database_url

    DATABASES = {
        'default': dj_database_url.parse(
            os.environ['DATABASE_URL'],
            conn_max_age=600,
            ssl_require=env_bool('DATABASE_SSL_REQUIRE', not DEBUG),
        )
    }
    if DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':
        DATABASES['default'].setdefault('OPTIONS', {})
        DATABASES['default']['OPTIONS'].setdefault('charset', 'utf8mb4')
        DATABASES['default']['OPTIONS'].setdefault(
            'init_command', "SET sql_mode='STRICT_TRANS_TABLES'"
        )
else:
    DATABASES = {
        'default': {
            'ENGINE': _ENGINES.get(DB_ENGINE, _ENGINES['postgresql']),
            'NAME': os.environ.get('DB_NAME', 'fonoDevDB'),
            'USER': os.environ.get('DB_USER', 'admin'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'secret'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432' if DB_ENGINE == 'postgresql' else '3306'),
        }
    }
    if DB_ENGINE == 'mysql':
        # utf8mb4 (no utf8 a secas) para soportar el set de caracteres completo
        # de Unicode (tildes, ñ, emoji en campos de texto libre).
        DATABASES['default']['OPTIONS'] = {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
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
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.environ.get('JWT_ACCESS_MINUTES', 60))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.environ.get('JWT_REFRESH_DAYS', 1))),
    'AUTH_HEADER_TYPES': ('Bearer',),

    # AGREGA ESTA LÍNEA:
    'USER_ID_FIELD': 'id_usuario',  # Aquí le decimos que use tu campo personalizado
    'USER_ID_CLAIM': 'user_id',    # Este es el nombre que tendrá dentro del token JSON
}

"""
    MANEJO DE IMAGENES
"""

# Carpeta física donde se guardan los archivos
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# URL base desde la cual se servirán en el navegador
MEDIA_URL = '/media/'