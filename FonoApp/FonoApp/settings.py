import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga variables desde el .env centralizado en la raíz del repo (compartido con
# FonoAppPortalMedico, ver Backend_Fono/.env y Backend_Fono/.env.example) — no sobreescribe
# variables ya definidas en el entorno real, por lo que en despliegue basta con exportar las
# variables del proveedor de hosting (ver FonoApp/.env.develop, FonoApp/.env.production.example).
load_dotenv(BASE_DIR.parent / '.env')


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
    'rest_framework_simplejwt',
    'cloudinary_storage',
    'cloudinary',
]

INSTALLED_APPS = DEV_APPS + BASE_APPS + FRAMEWORKS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # Sirve los archivos de STATIC_ROOT directamente desde el proceso Django. Hace
    # falta en cPanel/Passenger porque ahí no hay un Nginx/Apache al frente que
    # sirva estáticos aparte (a diferencia de 'runserver' en desarrollo, donde
    # django.contrib.staticfiles ya los sirve solo con DEBUG=True). Va justo
    # después de SecurityMiddleware, como pide la documentación de whitenoise.
    'whitenoise.middleware.WhiteNoiseMiddleware',
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

# Credenciales de Cloudinary (imágenes de banner, noticias, cuidados, información
# y voz). Salen del .env de la raíz del repo, NUNCA del código: son las mismas
# para el Portal Médico y este proyecto, igual que DATABASE_URL y SECRET_KEY.
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
}

# CloudinaryField (los campos de los modelos) no lee CLOUDINARY_STORAGE: usa la
# configuración global del SDK, que se fija aquí. secure=True para que las URLs
# generadas sean siempre https.
import cloudinary

cloudinary.config(
    cloud_name=CLOUDINARY_STORAGE['CLOUD_NAME'],
    api_key=CLOUDINARY_STORAGE['API_KEY'],
    api_secret=CLOUDINARY_STORAGE['API_SECRET'],
    secure=True,
)

# NOTA: DEFAULT_FILE_STORAGE ya no existe en Django 6 (se eliminó en 5.1); si se
# define, se ignora en silencio. El almacenamiento por defecto se declara en el
# diccionario STORAGES, más abajo en este archivo.

# Base de datos:
# - Desarrollo local: DATABASE_URL en el .env de la raíz del repo apunta a la BDD MySQL
#   "develop" compartida (ver .env.example en la raíz). Si no se define DATABASE_URL,
#   se arma con las variables DB_* de abajo (fallback, útil por ejemplo para Postgres local).
# - Despliegue: mismo mecanismo de DATABASE_URL (formato 12-factor: mysql://user:pass@host:port/nombre
#   o postgres://..., ver .env.develop / .env.production.example por proyecto).
# Motor de base de datos: 'postgresql' (default, igual que siempre) o 'mysql'
# (usado tanto en desarrollo local como en el despliegue en cPanel, ver deploy/mysql/).
# Definir DB_ENGINE=mysql solo afecta al camino DB_* de abajo; con DATABASE_URL el motor se detecta
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
            # Sin esto, Django reutiliza durante 10 minutos una conexion que el
            # MySQL remoto pudo cerrar antes por inactividad (su wait_timeout es
            # menor), y la peticion muere con
            # "(2006, 'MySQL server has gone away')". Pasa sobre todo en la
            # primera visita despues de un rato sin trafico.
            # conn_health_checks hace que Django compruebe que la conexion sigue
            # viva antes de reutilizarla, y la reabra si no; se conserva el
            # pooling sin arrastrar conexiones muertas.
            conn_health_checks=True,
            ssl_require=env_bool('DATABASE_SSL_REQUIRE', not DEBUG),
        )
    }
    if DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':
        DATABASES['default'].setdefault('OPTIONS', {})
        DATABASES['default']['OPTIONS'].setdefault('charset', 'utf8mb4')
        DATABASES['default']['OPTIONS'].setdefault(
            'init_command', "SET sql_mode='STRICT_TRANS_TABLES'"
        )
        # dj_database_url agrega OPTIONS['sslmode']='require' cuando ssl_require=True
        # (por defecto en producción, ver env_bool de arriba), pero 'sslmode' es un
        # nombre de psycopg2/Postgres: ni PyMySQL ni mysqlclient lo aceptan como
        # argumento de conexión y Django revienta con
        # "Connection.__init__() got an unexpected keyword argument 'sslmode'".
        # cPanel expone MySQL en localhost sin TLS, así que de todas formas no aplica.
        DATABASES['default']['OPTIONS'].pop('sslmode', None)
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

# Carpeta donde 'collectstatic' junta los estáticos de todas las apps (propios +
# los de django.contrib.admin y rest_framework) para servirlos en producción.
# Sin esto, 'python manage.py collectstatic' falla con
# "ImproperlyConfigured: ... without having set the STATIC_ROOT setting".
# En desarrollo (runserver) no se usa: django.contrib.staticfiles los sirve
# directo desde cada app mientras DEBUG=True, sin necesidad de recolectarlos.
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Compresión + serving de esos estáticos vía WhiteNoiseMiddleware (ver MIDDLEWARE).
# Se usa la variante "Compressed" (no "CompressedManifest") a propósito: la
# variante con manifiesto exige que cada estático referenciado en templates/CSS
# exista sin errores en el primer collectstatic, y falla duro si no — con
# "Compressed" a secas el despliegue no se cae por un estático de una librería
# de terceros mal referenciado.
STORAGES = {
    # Archivos subidos: Cloudinary (equivalente en Django 6 del antiguo
    # DEFAULT_FILE_STORAGE). Los campos CloudinaryField suben por el SDK sin
    # pasar por aquí, pero cualquier FileField/ImageField que se agregue en el
    # futuro debe ir a la nube también, no al disco del hosting.
    'default': {
        'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}


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