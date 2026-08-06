import os

from django.core.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):
    """
    Igual que el 'runserver' de Django, pero toma el puerto por defecto de la
    variable de entorno PORT (ver .env) en vez de dejarlo fijo en 8000.

    Así, FonoApp y FonoAppPortalMedico pueden levantarse en simultáneo cada
    uno con 'python manage.py runserver' sin escribir el puerto a mano y sin
    pisarse entre sí (ver PORT en FonoApp/.env vs FonoAppPortalMedico/.env).

    Se puede seguir indicando un puerto puntual que sobrescriba el de PORT:
        python manage.py runserver 9000
    """
    default_port = os.environ.get('PORT', RunserverCommand.default_port)
