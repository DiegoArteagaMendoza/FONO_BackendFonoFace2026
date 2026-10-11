from django.core.management.base import BaseCommand

from PmVideo.models import PmVideo, DIAS_VIGENCIA
from PmTerapia.models import PmVideoProgreso, PROGRESO_DIAS_VIGENCIA


class Command(BaseCommand):
    """
    Elimina los videos que ya cumplieron su vigencia.

    Cubre los dos tipos de video que vencen:
      - Videos de síntomas (PmVideo): 30 días.
      - Videos de progreso de terapia (PmVideoProgreso): 7 días.
    Los videos de ejemplo de los ejercicios NO vencen y no se tocan.

    En ambos casos borra el archivo de Cloudinary y deja el registro marcado
    como vencido para conservar la trazabilidad (y, en los de progreso, la
    retroalimentación del fonoaudiólogo, que el paciente sigue leyendo).

    USO:
        python manage.py limpiar_videos_vencidos
        python manage.py limpiar_videos_vencidos --simular   (solo muestra, no borra)

    Conviene programarlo una vez al día (cron del hosting, ver deploy/scripts/).
    """

    help = (
        f'Elimina los videos de síntomas que superaron los {DIAS_VIGENCIA} días y los de '
        f'progreso de terapia que superaron los {PROGRESO_DIAS_VIGENCIA}.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--simular',
            action='store_true',
            help='Muestra qué videos se eliminarían, sin borrar nada.',
        )

    def handle(self, *args, **opciones):
        simular = opciones['simular']

        total = self._limpiar_sintomas(simular) + self._limpiar_progreso(simular)

        if total == 0:
            self.stdout.write(self.style.SUCCESS('No hay videos vencidos por eliminar.'))
        elif simular:
            self.stdout.write(self.style.WARNING(f'[SIMULACIÓN] Se eliminarían {total} video(s) en total.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Listo: {total} video(s) eliminado(s) en total.'))

    # ------------------------------------------------------------------
    # Videos de síntomas
    # ------------------------------------------------------------------

    def _limpiar_sintomas(self, simular):
        vencidos = PmVideo.objects.vencidos()
        total = vencidos.count()
        if total == 0:
            return 0

        self.stdout.write(f'Videos de síntomas vencidos ({DIAS_VIGENCIA} días): {total}')
        for video in vencidos:
            etiqueta = f'#{video.id_video} de {video.cliente} (subido el {video.fecha_subida:%d/%m/%Y})'
            if simular:
                self.stdout.write(f'  - se eliminaría {etiqueta}')
            elif PmVideo.objects.eliminar(video.id_video, PmVideo.MotivoEliminacion.VENCIMIENTO):
                self.stdout.write(f'  Eliminado {etiqueta}')
        return total

    # ------------------------------------------------------------------
    # Videos de progreso de terapia
    # ------------------------------------------------------------------

    def _limpiar_progreso(self, simular):
        vencidos = PmVideoProgreso.objects.vencidos().select_related('plan_ejercicio__ejercicio')
        total = vencidos.count()
        if total == 0:
            return 0

        self.stdout.write(f'Videos de progreso vencidos ({PROGRESO_DIAS_VIGENCIA} días): {total}')
        for video in vencidos:
            etiqueta = f'#{video.id_video} ({video.plan_ejercicio.ejercicio.nombre}, subido el {video.fecha_subida:%d/%m/%Y})'
            if simular:
                self.stdout.write(f'  - se eliminaría {etiqueta}')
            elif PmVideoProgreso.objects.eliminar(video, PmVideoProgreso.MotivoEliminacion.VENCIMIENTO):
                self.stdout.write(f'  Eliminado {etiqueta}')
        return total
