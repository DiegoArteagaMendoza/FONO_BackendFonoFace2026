from django.db import models
from cloudinary.models import CloudinaryField

from PmMedico.models import PM_Profesional
from PmTerapia.queryset import PmEjercicio_Queryset
from Security.archivos import borrar_de_cloudinary

# ==========================================================================
# REGLAS DEL NEGOCIO (centralizadas para no repetirlas en el código)
# ==========================================================================

# Video de ejemplo de un ejercicio: corto a propósito. Es una demostración de
# cómo se hace, no una clase; 15 segundos obligan a ir al grano y pesan poco.
EJEMPLO_DURACION_MAXIMA_SEGUNDOS = 15

# 15 segundos desde un celular rondan los 8-20 MB según la calidad.
EJEMPLO_TAMANO_MAXIMO_MB = 30

# Tope de ejercicios asignables en un plan. Lo pidió el fonoaudiólogo: más de
# tres tareas diarias no se cumplen. Se usa en la entrega del plan de terapia.
EJERCICIOS_MAXIMOS_POR_PLAN = 3


class PmEjercicio(models.Model):
    """
    Un ejercicio del catálogo privado de un fonoaudiólogo.

    Es lo que después asigna a sus pacientes en un plan de terapia: un nombre,
    las instrucciones y un video corto mostrando cómo se hace. A diferencia de
    los videos de síntomas y de progreso, el de ejemplo es PERMANENTE: no tiene
    fecha de expiración y el comando de limpieza no lo toca. Es material del
    profesional, no del paciente, y sirve mientras el ejercicio exista.
    """

    id_ejercicio = models.AutoField('Código del ejercicio', primary_key=True)

    profesional = models.ForeignKey(
        PM_Profesional,
        on_delete=models.CASCADE,
        related_name='ejercicios',
        verbose_name='Fonoaudiólogo dueño del ejercicio',
    )

    nombre = models.CharField(max_length=120, verbose_name='Nombre del ejercicio')
    instrucciones = models.TextField(verbose_name='Cómo se hace')

    # resource_type='video' para que Cloudinary lo trate como material
    # audiovisual (streaming, transcodificación), igual que en PmVideo.
    video_ejemplo = CloudinaryField(
        'video de ejemplo',
        folder='pm/videos/ejercicios/',
        resource_type='video',
    )
    duracion_segundos = models.PositiveIntegerField(verbose_name='Duración del ejemplo en segundos')

    # Borrado lógico: un ejercicio quitado del catálogo sigue existiendo para
    # los planes que ya lo tenían asignado.
    estado = models.BooleanField(default=True, verbose_name='En el catálogo')

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    objects = PmEjercicio_Queryset.as_manager()

    class Meta:
        verbose_name = 'Ejercicio de terapia'
        verbose_name_plural = 'Ejercicios de terapia'
        ordering = ['-fecha_creacion']

    def esta_en_uso(self):
        """
        True si algún plan de terapia lo tiene asignado.

        El modelo del plan llega en la siguiente entrega; hasta entonces ningún
        plan puede referenciarlo. Se deja el método para que 'eliminar' ya lo
        respete y no haya que tocar el queryset después.
        """
        relacion = getattr(self, 'asignaciones', None)
        return relacion.exists() if relacion is not None else False

    def eliminar_archivo_fisico(self):
        """Borra el video de ejemplo de Cloudinary. El registro no se toca."""
        if self.video_ejemplo:
            borrar_de_cloudinary(self.video_ejemplo)

    def __str__(self):
        return f'{self.nombre} ({self.profesional})'
