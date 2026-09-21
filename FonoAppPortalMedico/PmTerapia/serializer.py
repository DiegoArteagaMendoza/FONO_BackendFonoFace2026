from rest_framework import serializers

from Security.archivos import url_absoluta
from Security.validacion_video import validar_archivo, validar_duracion
from PmTerapia.models import (
    PmEjercicio,
    EJEMPLO_DURACION_MAXIMA_SEGUNDOS,
    EJEMPLO_TAMANO_MAXIMO_MB,
)


class PmEjercicioSerializer(serializers.ModelSerializer):
    """
    Un ejercicio del catálogo, para el fonoaudiólogo que lo administra.

    No se entrega 'profesional': el dueño sale del token en la vista y quien
    lee ya sabe que es suyo. 'estado' tampoco: lo que se lista es lo vigente.
    """

    class Meta:
        model = PmEjercicio
        fields = [
            'id_ejercicio',
            'nombre',
            'instrucciones',
            'video_ejemplo',
            'duracion_segundos',
            'fecha_creacion',
            'fecha_actualizacion',
        ]
        read_only_fields = ['id_ejercicio', 'fecha_creacion', 'fecha_actualizacion']

    def to_representation(self, instance):
        """CloudinaryField serializa el public_id; el frontend necesita la URL."""
        datos = super().to_representation(instance)
        datos['video_ejemplo'] = url_absoluta(instance.video_ejemplo)
        return datos

    # Las reglas del archivo viven en Security/validacion_video.py, compartidas
    # con los otros videos del portal; aquí solo van los límites del ejemplo.
    def validate_duracion_segundos(self, value):
        return validar_duracion(value, EJEMPLO_DURACION_MAXIMA_SEGUNDOS)

    def validate_video_ejemplo(self, archivo):
        return validar_archivo(archivo, EJEMPLO_TAMANO_MAXIMO_MB)


class PmEjercicioEditarSerializer(PmEjercicioSerializer):
    """
    Edición: el video y su duración son opcionales.

    Cambiar solo el nombre o las instrucciones no debería obligar a volver a
    subir el video. Si viene un archivo nuevo, tiene que venir con su duración;
    eso lo comprueba validate().
    """

    class Meta(PmEjercicioSerializer.Meta):
        extra_kwargs = {
            'video_ejemplo': {'required': False},
            'duracion_segundos': {'required': False},
        }

    def validate(self, datos):
        if 'video_ejemplo' in datos and 'duracion_segundos' not in datos:
            raise serializers.ValidationError(
                {'duracion_segundos': 'Si cambias el video, indica también su duración.'}
            )
        return datos
