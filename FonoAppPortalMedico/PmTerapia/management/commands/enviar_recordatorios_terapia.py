from django.core.management.base import BaseCommand

from PmTerapia.correos import enviar_recordatorio_periodo
from PmTerapia.models import PmPlanTerapia


class Command(BaseCommand):
    """
    Recuerda a los pacientes los periodos de terapia que cerraron sin videos.

    Para cada plan activo mira solo su último periodo cerrado: si le faltó el
    video de algún ejercicio y todavía no se le recordó, manda un correo al
    paciente y deja anotado el periodo en ultimo_periodo_recordado. Un correo
    por periodo incumplido, nunca dos (la selección está en
    PmPlanTerapia_Queryset.recordatorios_pendientes).

    Si el correo no sale (SMTP caído, paciente sin correo), el periodo NO se
    marca: con planes semanales o quincenales, la corrida del día siguiente
    lo reintenta; con planes diarios ya habrá cerrado otro periodo y se
    recuerda ese.

    USO:
        python manage.py enviar_recordatorios_terapia
        python manage.py enviar_recordatorios_terapia --simular   (solo muestra, no envía)

    Conviene programarlo una vez al día, temprano, en la zona horaria de Chile
    (cron del hosting, ver deploy/scripts/crontab_portalmedico.txt). Sin
    EMAIL_HOST configurado, los correos salen por consola.
    """

    help = 'Envía un recordatorio a los pacientes cuyo último periodo de terapia cerró sin todos sus videos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--simular',
            action='store_true',
            help='Muestra a quién se le enviaría el recordatorio, sin enviar nada.',
        )

    def handle(self, *args, **opciones):
        simular = opciones['simular']

        pendientes = PmPlanTerapia.objects.recordatorios_pendientes()
        if not pendientes:
            self.stdout.write(self.style.SUCCESS('No hay recordatorios por enviar.'))
            return

        self.stdout.write(f'Planes con el último periodo cerrado sin cumplir: {len(pendientes)}')

        enviados = 0
        for plan, numero, faltan in pendientes:
            etiqueta = (
                f'plan #{plan.pk} de {plan.cliente} (periodo {numero + 1}, '
                f'falta: {", ".join(faltan)})'
            )
            if simular:
                self.stdout.write(f'  - se recordaría {etiqueta}')
                continue

            if enviar_recordatorio_periodo(plan, numero, faltan):
                PmPlanTerapia.objects.marcar_recordado(plan, numero)
                enviados += 1
                self.stdout.write(f'  Recordado {etiqueta}')
            else:
                self.stdout.write(self.style.WARNING(f'  No se pudo enviar: {etiqueta}'))

        if simular:
            self.stdout.write(self.style.WARNING(f'[SIMULACIÓN] Se enviarían {len(pendientes)} recordatorio(s).'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Listo: {enviados} recordatorio(s) enviado(s).'))
