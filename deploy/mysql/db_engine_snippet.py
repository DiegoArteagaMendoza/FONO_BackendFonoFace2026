# ─────────────────────────────────────────────────────────────────────────
# Reemplazo del bloque DATABASES actual de settings.py, para poder elegir el
# motor (PostgreSQL o MySQL) vía variable de entorno SIN romper nada de lo
# que hay hoy: si no defines DB_ENGINE, el comportamiento es IDÉNTICO al
# actual (PostgreSQL), tanto en desarrollo (Docker) como si no hay
# DATABASE_URL definida.
#
# CÓMO USARLO:
#   Reemplazar el bloque que hoy dice:
#
#       if os.environ.get('DATABASE_URL'):
#           import dj_database_url
#           DATABASES = { 'default': dj_database_url.parse(...) }
#       else:
#           DATABASES = { 'default': { 'ENGINE': 'django.db.backends.postgresql', ... } }
#
#   por el contenido de este archivo, en:
#     - FonoApp/FonoApp/settings.py
#     - FonoAppPortalMedico/FonoAppPM/settings.py
#
#   (en ambos el bloque es prácticamente igual; en PortalMedico no existe
#   DATABASE_SSL_REQUIRE con el mismo nombre de variable "not DEBUG" — usar
#   la versión que ya tiene cada archivo como base y solo cambiar la parte
#   de ENGINE/OPTIONS como se ve abajo).
#
# NADA de esto exige tocar docker-compose.yml ni el flujo de desarrollo
# local: mientras no definas DB_ENGINE=mysql (ni localmente ni en el
# hosting), todo sigue funcionando contra Postgres exactamente igual.
# ─────────────────────────────────────────────────────────────────────────

# Motor de base de datos: 'postgresql' (default, igual que hoy) o 'mysql'.
DB_ENGINE = os.environ.get('DB_ENGINE', 'postgresql').strip().lower()

_ENGINES = {
    'postgresql': 'django.db.backends.postgresql',
    'mysql': 'django.db.backends.mysql',
}

if os.environ.get('DATABASE_URL'):
    import dj_database_url

    # dj_database_url detecta el motor automáticamente por el esquema de la
    # URL: "postgres://..." -> postgresql, "mysql://..." -> mysql. No hace
    # falta usar DB_ENGINE en este camino, pero igual definimos OPTIONS de
    # charset para MySQL si corresponde.
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
        # Sin esto, Django emite el warning mysql.W002 y MariaDB silencia
        # truncamientos/errores de datos en vez de rechazarlos.
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
        # de Unicode (tildes, ñ, emoji en campos de texto libre como
        # "contenido" o "descripcion"). MariaDB/MySQL modernos (los que trae
        # cPanel) ya usan InnoDB con innodb_large_prefix por defecto, así que
        # no hace falta tocar ROW_FORMAT para los campos únicos/indexados de
        # este proyecto (RUT, email — todos cortos).
        DATABASES['default']['OPTIONS'] = {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        }
