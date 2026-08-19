from rest_framework import serializers

from PmVideo.models import (
    PmVideo,
    DURACION_MAXIMA_SEGUNDOS,
    TAMANO_MAXIMO_MB,
    EXTENSIONES_PERMITIDAS,
)


class PmVideoSerializer(serializers.ModelSerializer):
    # Campos calculados, útiles para que el frontend muestre el tiempo restante
    dias_restantes = serializers.IntegerField(read_only=True)
    esta_vigente = serializers.BooleanField(read_only=True)

    class Meta:
        model = PmVideo
        fields = [
            'id_video',
            'cliente',
            'cita',
            'video',
            'descripcion',
            'duracion_segundos',
            'fecha_subida',
            'fecha_expiracion',
            'estado',
            'fecha_eliminacion',
            'motivo_eliminacion',
            'dias_restantes',
            'esta_vigente',
        ]
        read_only_fields = [
            'id_video',
            # El dueño se toma del token en la vista (serializer.save(cliente=...)),
            # nunca del cuerpo de la petición: así nadie sube videos a nombre de otro.
            'cliente',
            'fecha_subida',
            'fecha_expiracion',
            'estado',
            'fecha_eliminacion',
            'motivo_eliminacion',
        ]
        extra_kwargs = {
            'cita': {'required': False, 'allow_null': True},
        }

    def validate(self, datos):
        """
        Si el video se asocia a una cita, esta debe pertenecer al mismo
        cliente, admitir la carga de video y seguir reservada (no cancelada
        ni ya realizada).
        """
        cita = datos.get('cita')

        # OJO: 'cliente' es de solo lectura (el dueño se toma del token en la
        # vista), así que NO llega dentro de 'datos'. La vista lo entrega por
        # contexto; sin esto la comprobación de propiedad de la cita quedaría
        # siempre en falso y cualquiera podría colgar su video de una cita ajena.
        cliente = datos.get('cliente') or self.context.get('cliente')

        if cita:
            if cliente and cita.cliente_id != cliente.pk:
                raise serializers.ValidationError({'cita': 'La cita no pertenece a este cliente.'})
            if not cita.permite_carga_video:
                raise serializers.ValidationError({'cita': 'Esta cita no admite la carga de un video.'})
            if not cita.esta_activa:
                raise serializers.ValidationError(
                    {'cita': 'Solo se puede adjuntar un video a una cita reservada (no cancelada ni realizada).'}
                )

        return datos

    def validate_duracion_segundos(self, value):
        """El video no puede superar los 30 segundos."""
        if value <= 0:
            raise serializers.ValidationError('La duración debe ser mayor a 0 segundos.')

        if value > DURACION_MAXIMA_SEGUNDOS:
            raise serializers.ValidationError(
                f'El video no puede durar más de {DURACION_MAXIMA_SEGUNDOS} segundos '
                f'(el enviado dura {value}).'
            )
        return value

    def validate_video(self, archivo):
        """Valida el formato y el peso del archivo subido."""
        nombre = archivo.name.lower()
        extension = nombre.rsplit('.', 1)[-1] if '.' in nombre else ''

        if extension not in EXTENSIONES_PERMITIDAS:
            raise serializers.ValidationError(
                f'Formato no permitido (.{extension}). '
                f'Use uno de estos: {", ".join(EXTENSIONES_PERMITIDAS)}.'
            )

        tamano_maximo_bytes = TAMANO_MAXIMO_MB * 1024 * 1024
        if archivo.size > tamano_maximo_bytes:
            tamano_mb = archivo.size / (1024 * 1024)
            raise serializers.ValidationError(
                f'El video pesa {tamano_mb:.1f} MB y el máximo permitido es {TAMANO_MAXIMO_MB} MB.'
            )

        return archivo
