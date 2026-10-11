"""
Validación de un archivo de video antes de subirlo a Cloudinary.

Las mismas tres reglas —formato, peso y duración declarada— las necesitan los
tres videos del Portal Médico: el de síntomas (PmVideo), el de ejemplo de un
ejercicio y el de progreso de terapia (PmTerapia). Cambian los límites, no la
regla, así que viven aquí una sola vez y cada serializer las llama con los
suyos.

La duración la declara el navegador: el servidor no puede medirla sin ffmpeg.
Se valida igual porque es lo que se guarda, y el frontend ya la comprobó con
el mismo tope; si no coinciden, manda el servidor.
"""
from rest_framework import serializers

# Los formatos son los mismos para cualquier video del portal.
EXTENSIONES_PERMITIDAS = ['mp4', 'webm', 'mov']


def validar_archivo(archivo, tamano_maximo_mb):
    """Formato y peso del archivo. Lanza ValidationError o devuelve el archivo."""
    nombre = archivo.name.lower()
    extension = nombre.rsplit('.', 1)[-1] if '.' in nombre else ''

    if extension not in EXTENSIONES_PERMITIDAS:
        raise serializers.ValidationError(
            f'Formato no permitido (.{extension}). '
            f'Use uno de estos: {", ".join(EXTENSIONES_PERMITIDAS)}.'
        )

    if archivo.size > tamano_maximo_mb * 1024 * 1024:
        tamano_mb = archivo.size / (1024 * 1024)
        raise serializers.ValidationError(
            f'El video pesa {tamano_mb:.1f} MB y el máximo permitido es {tamano_maximo_mb} MB.'
        )

    return archivo


def validar_duracion(segundos, duracion_maxima_segundos):
    """Duración declarada. Lanza ValidationError o devuelve el valor."""
    if segundos <= 0:
        raise serializers.ValidationError('La duración debe ser mayor a 0 segundos.')

    if segundos > duracion_maxima_segundos:
        raise serializers.ValidationError(
            f'El video no puede durar más de {duracion_maxima_segundos} segundos '
            f'(el enviado dura {segundos}).'
        )

    return segundos
