from rest_framework import serializers

from Security.archivos import url_absoluta
from Security.validacion_video import validar_archivo, validar_duracion
from PmVideo.models import PmVideo, DURACION_MAXIMA_SEGUNDOS, TAMANO_MAXIMO_MB


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

    def to_representation(self, instance):
        """
        El campo 'video' es un CloudinaryField: serializado tal cual entrega el
        public_id, no una URL. Se reemplaza por la URL https real para que el
        <video> del frontend pueda reproducirlo directo.
        """
        datos = super().to_representation(instance)
        datos['video'] = url_absoluta(instance.video)
        return datos

    def validate(self, datos):
        """
        Si el video se asocia a una cita, esta debe pertenecer al mismo
        cliente, admitir la carga de video y seguir reservada (no cancelada
        ni ya realizada).
        """
        cita = datos.get('cita') or self.context.get('cita')

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

    # Las reglas del archivo viven en Security/validacion_video.py, compartidas
    # con los videos de terapia; aquí solo se ponen los límites de este tipo.
    def validate_duracion_segundos(self, value):
        return validar_duracion(value, DURACION_MAXIMA_SEGUNDOS)

    def validate_video(self, archivo):
        return validar_archivo(archivo, TAMANO_MAXIMO_MB)


class PmVideoSeguimientoSerializer(PmVideoSerializer):
    """
    El mismo video, visto por quien llega con su código de seguimiento y sin
    sesión iniciada.

    Cambia en dos cosas respecto de PmVideoSerializer:

    1. 'cita' es de solo lectura. La cita la resuelve la vista a partir del
       código y viaja por contexto; si se aceptara desde el cuerpo, alguien con
       un código válido podría colgar su video de la cita de otra persona.
    2. No se entrega ningún identificador: ni 'cliente', ni 'cita', ni
       'id_video'. Es la regla 4 del Specs y el mismo criterio de
       PmCitaSeguimientoSerializer. El video se identifica por su cita, que ya
       viene dada por el código, así que ningún id hace falta para gestionarlo.
    """

    class Meta(PmVideoSerializer.Meta):
        fields = [
            'video',
            'descripcion',
            'duracion_segundos',
            'fecha_subida',
            'fecha_expiracion',
            'dias_restantes',
            'esta_vigente',
        ]
        # Lo único que llega desde el formulario. Todo lo demás lo pone el
        # servidor: la cita sale del código y el dueño, de esa cita.
        read_only_fields = [
            'fecha_subida',
            'fecha_expiracion',
            'dias_restantes',
            'esta_vigente',
        ]
        extra_kwargs = {}
