from django.core.management.base import BaseCommand

from PmVideo.models import PmVideo, DIAS_VIGENCIA


class Command(BaseCommand):
    """
    Elimina los videos que ya cumplieron sus 30 días.

    Borra el archivo físico del disco y deja el registro marcado como vencido
    para conservar la trazabilidad de que ese video existió.

    USO:
        python manage.py limpiar_videos_vencidos
        python manage.py limpiar_videos_vencidos --simular   (solo muestra, no borra)

    Conviene programarlo una vez al día (Programador de tareas de Windows o cron).
    """

    help = f'Elimina los videos de síntomas que superaron los {DIAS_VIGENCIA} días de vigencia.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--simular',
            action='store_true',
            help='Muestra qué videos se eliminarían, sin borrar nada.',
        )

    def handle(self, *args, **opciones):
        simular = opciones['simular']
        vencidos = PmVideo.objects.vencidos()
        total = vencidos.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS('No hay videos vencidos por eliminar.'))
            return

        if simular:
            self.stdout.write(self.style.WARNING(f'[SIMULACIÓN] Se eliminarían {total} video(s):'))
            for video in vencidos:
                self.stdout.write(
                    f'  - Video #{video.id_video} de {video.cliente} '
                    f'(subido el {video.fecha_subida:%d/%m/%Y})'
                )
            return

        eliminados = 0
        for video in vencidos:
            if PmVideo.objects.eliminar(video.id_video, PmVideo.MotivoEliminacion.VENCIMIENTO):
                eliminados += 1
                self.stdout.write(f'  Eliminado video #{video.id_video} de {video.cliente}')

        self.stdout.write(self.style.SUCCESS(f'Listo: {eliminados} video(s) eliminado(s).'))
