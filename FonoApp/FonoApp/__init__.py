# Django importa internamente el módulo "MySQLdb" cuando DATABASES usa el motor
# 'django.db.backends.mysql' (ver settings.py, DB_ENGINE=mysql / DATABASE_URL=mysql://...).
# PyMySQL no se llama así, pero incluye un modo de compatibilidad que se activa con
# este shim de 2 líneas. Es seguro dejarlo siempre presente: mientras la app siga
# usando PostgreSQL (comportamiento por defecto), Django nunca pide el módulo
# MySQLdb y este import simplemente no se usa.
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    # PyMySQL no está instalado (ej. entorno que solo usa Postgres localmente).
    pass
