from django.db import models
from django.utils import timezone


class PmVideo_Queryset(models.QuerySet):

    def vigentes(self):
        """
        Videos que siguen disponibles: no eliminados y dentro de los 30 días.
        Se usa en todas las consultas para que un video vencido nunca se entregue,
        incluso si el archivo todavía no fue purgado del disco.
        """
        return self.filter(estado=True, fecha_expiracion__gt=timezone.now())

    def vencidos(self):
        """Videos cuyo plazo de 30 días ya se cumplió y siguen sin eliminarse."""
        return self.filter(estado=True, fecha_expiracion__lte=timezone.now())

    def del_cliente(self, id_cliente):
        """Videos vigentes de un cliente puntual."""
        return self.vigentes().filter(cliente_id=id_cliente)

    def eliminar(self, id_video, motivo):
        """
        Elimina un video: borra el archivo físico del disco y marca el registro
        con el motivo, conservándolo para trazabilidad.
        Retorna True si se eliminó, False si no existía o ya estaba eliminado.
        """
        video = self.filter(id_video=id_video, estado=True).first()

        if not video:
            return False

        video.eliminar_archivo_fisico()
        video.estado = False
        video.motivo_eliminacion = motivo
        video.fecha_eliminacion = timezone.now()
        video.save(update_fields=['estado', 'motivo_eliminacion', 'fecha_eliminacion', 'video'])
        return True
