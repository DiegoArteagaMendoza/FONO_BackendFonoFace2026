import os

from django.core.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):
    """
    Igual que el 'runserver' de Django, pero toma el puerto por defecto de la
    variable de entorno PORT (ver .env) en vez del 8000 estándar de Django,
    que ya usa FonoApp. El valor por defecto de PmMedico es 8001.

    Así, FonoApp y FonoAppPortalMedico pueden levantarse en simultáneo cada
    uno con 'python manage.py runserver' sin escribir el puerto a mano y sin
    pisarse entre sí.

    Se puede seguir indicando un puerto puntual que sobrescriba el de PORT:
        python manage.py runserver 9000
    """
    default_port = os.environ.get('PORT', '8001')
