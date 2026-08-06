import math
from datetime import timedelta

from django.db import models
from django.utils import timezone

from PmCliente.models import PmCliente
from PmVideo.queryset import PmVideo_Queryset

# ==========================================================================
# REGLAS DEL NEGOCIO (centralizadas para no repetirlas en el código)
# ==========================================================================

# Duración máxima permitida del video
DURACION_MAXIMA_SEGUNDOS = 30

# Días que el video permanece disponible antes de eliminarse
DIAS_VIGENCIA = 30

# Peso máximo del archivo. 30 segundos de video grabado desde un celular
# rondan los 15-40 MB según la calidad, por eso se deja en 50 MB.
TAMANO_MAXIMO_MB = 50

# Formatos aceptados
EXTENSIONES_PERMITIDAS = ['mp4', 'webm', 'mov']


class PmVideo(models.Model):
    """
    Video de máximo 30 segundos que el cliente sube para mostrar sus síntomas.

    El archivo permanece disponible 30 días desde la subida; después se elimina
    (ver el comando `limpiar_videos_vencidos`). El médico también puede ordenar
    su eliminación antes de ese plazo.
    """

    class MotivoEliminacion(models.TextChoices):
        VENCIMIENTO = 'VE', 'Vencimiento de los 30 días'
        ORDEN_MEDICA = 'OM', 'Eliminado por orden del médico'

    id_video = models.AutoField("Codigo registro video", primary_key=True)

    # Dueño del video
    cliente = models.ForeignKey(
        PmCliente,
        on_delete=models.CASCADE,
        related_name='videos',
        verbose_name='Cliente que sube el video'
    )

    # NOTA: cuando exista el modelo de citas (PmCita) se agrega aquí la relación
    # con la cita médica correspondiente:
    # cita = models.ForeignKey('PmCita.PmCita', on_delete=models.CASCADE,
    #                          related_name='videos', null=True, blank=True)

    # Archivo y contenido
    video = models.FileField(upload_to='pm/videos/sintomas/', verbose_name='Video de síntomas')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción de los síntomas')
    duracion_segundos = models.PositiveIntegerField(verbose_name='Duración en segundos')

    # Vigencia
    fecha_subida = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de subida')
    fecha_expiracion = models.DateTimeField(verbose_name='Fecha en que deja de estar disponible')

    # Control y trazabilidad
    estado = models.BooleanField(default=True, verbose_name='Disponible')
    fecha_eliminacion = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de eliminación')
    motivo_eliminacion = models.CharField(
        max_length=2,
        choices=MotivoEliminacion.choices,
        null=True,
        blank=True,
        verbose_name='Motivo de la eliminación'
    )

    objects = PmVideo_Queryset.as_manager()

    class Meta:
        db_table = 'PmVideo'
        managed = True
        verbose_name = 'Video de síntomas'
        verbose_name_plural = 'Videos de síntomas'
        ordering = ['-fecha_subida']

    def save(self, *args, **kwargs):
        # Al crearse, la fecha de expiración se calcula sola: 30 días desde hoy
        if not self.fecha_expiracion:
            self.fecha_expiracion = timezone.now() + timedelta(days=DIAS_VIGENCIA)
        super().save(*args, **kwargs)

    @property
    def esta_vigente(self):
        """True si el video sigue disponible (no eliminado y dentro de los 30 días)."""
        return self.estado and self.fecha_expiracion > timezone.now()

    @property
    def dias_restantes(self):
        """
        Días que le quedan al video antes de eliminarse (0 si ya venció).
        Se redondea hacia arriba: un video recién subido muestra 30 y no 29.
        """
        if not self.estado:
            return 0
        segundos = (self.fecha_expiracion - timezone.now()).total_seconds()
        return max(math.ceil(segundos / 86400), 0)

    def eliminar_archivo_fisico(self):
        """
        Borra el archivo del disco conservando el registro para trazabilidad.
        Se usa tanto al vencer los 30 días como al eliminar por orden médica.
        """
        if self.video:
            self.video.delete(save=False)

    def __str__(self):
        return f'Video #{self.id_video} de {self.cliente} ({self.duracion_segundos}s)'
