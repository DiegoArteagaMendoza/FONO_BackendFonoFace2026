# ─────────────────────────────────────────────────────────────────────────
# Solo necesario si vas a usar el driver PyMySQL (recomendado para cPanel,
# ver requirements-mysql.txt) en vez de mysqlclient.
#
# Django importa internamente el módulo "MySQLdb" cuando ENGINE es
# 'django.db.backends.mysql'. PyMySQL no se llama así, pero incluye un modo
# de compatibilidad que se registra con este shim de 2 líneas.
#
# CÓMO USARLO: pegar este contenido al PRINCIPIO de:
#   - FonoApp/FonoApp/__init__.py
#   - FonoAppPortalMedico/FonoAppPM/__init__.py
#
# (ambos archivos están vacíos hoy, así que no hay nada que preservar).
# Es seguro dejarlo siempre presente, incluso si DB_ENGINE sigue en
# 'postgresql': el import de pymysql simplemente no se usa en ese caso
# porque Django nunca llega a pedir el módulo MySQLdb. Aun así, si prefieres
# no depender de PyMySQL en absoluto mientras no migres, puedes envolverlo en
# un try/except como se muestra abajo.
# ─────────────────────────────────────────────────────────────────────────

try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    # PyMySQL no está instalado (ej. todavía no se agregó requirements-mysql.txt
    # o se está corriendo en un entorno que usa Postgres exclusivamente).
    pass
