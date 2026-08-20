from rest_framework import serializers

from PmMedico.models import PM_Profesional
from PmCita.models import (
    PmCita,
    PmDisponibilidad,
    DURACION_MINUTOS_MINIMA,
    DURACION_MINUTOS_MAXIMA,
)


class PmCitaSerializer(serializers.ModelSerializer):
    """
    Representación completa de la cita, de solo lectura: la creación y cada
    transición de estado (cancelar, posponer, marcar realizada) se hacen a
    través de los métodos de PmCita_Queryset (invocados desde las vistas),
    que son quienes aplican las reglas de negocio (anticipación mínima,
    solape de horarios, tope de reprogramaciones, etc.).
    """
    esta_activa = serializers.BooleanField(read_only=True)
    ya_paso = serializers.BooleanField(read_only=True)

    class Meta:
        model = PmCita
        fields = [
            'id_cita', 'cliente', 'profesional', 'fecha_hora', 'duracion_minutos',
            'motivo_consulta', 'estado', 'permite_carga_video',
            'fecha_creacion', 'fecha_actualizacion',
            'motivo_cancelacion', 'fecha_cancelacion', 'cancelada_por',
            'fecha_hora_original', 'veces_reprogramada', 'motivo_reprogramacion',
            'reprogramada_por', 'fecha_ultima_reprogramacion',
            'fecha_marcada_realizada',
            'esta_activa', 'ya_paso',
        ]
        read_only_fields = fields


# ==========================================================================
# SERIALIZERS DE ENTRADA (validan el body de cada acción; no tocan el modelo
# directamente, los datos ya validados se pasan a los métodos del queryset)
# ==========================================================================

# El cliente dueño de la acción NO viaja en el cuerpo de estas peticiones: se
# toma del token de sesión del paciente en la vista (request.user). Antes sí se
# enviaba, porque PmCliente no tenía sesión propia; ahora que la tiene, aceptar
# un id_cliente del body permitiría reservar, cancelar o posponer citas a nombre
# de otra persona con solo conocer su id.


class PmCitaReservarSerializer(serializers.Serializer):
    """Body esperado por POST /api/pm/citas/reservar/ (paciente autenticado)."""
    id_profesional = serializers.PrimaryKeyRelatedField(queryset=PM_Profesional.objects.activos())
    fecha_hora = serializers.DateTimeField()
    motivo_consulta = serializers.CharField(required=False, allow_blank=True, default='')
    duracion_minutos = serializers.IntegerField(
        required=False, min_value=DURACION_MINUTOS_MINIMA, max_value=DURACION_MINUTOS_MAXIMA
    )


class PmCitaClienteCancelarSerializer(serializers.Serializer):
    """Body esperado al cancelar desde el lado del cliente (paciente autenticado)."""
    motivo = serializers.CharField(required=False, allow_blank=True, default='')


class PmCitaClientePosponerSerializer(serializers.Serializer):
    """Body esperado al posponer desde el lado del cliente (paciente autenticado)."""
    fecha_hora = serializers.DateTimeField()
    motivo = serializers.CharField(required=False, allow_blank=True, default='')


class PmCitaCancelarSerializer(serializers.Serializer):
    """Body esperado al cancelar desde el lado del profesional (autenticado)."""
    motivo = serializers.CharField(required=False, allow_blank=True, default='')


class PmCitaPosponerSerializer(serializers.Serializer):
    """Body esperado al posponer desde el lado del profesional (autenticado)."""
    fecha_hora = serializers.DateTimeField()
    motivo = serializers.CharField(required=False, allow_blank=True, default='')


# ==========================================================================
# DISPONIBILIDAD (bloques que el profesional publica)
# ==========================================================================

class PmDisponibilidadSerializer(serializers.ModelSerializer):
    """
    Bloque tal como lo ve el profesional dueño: incluye si ya fue tomado y por
    qué cita, para que pueda distinguir de un vistazo lo libre de lo agendado.
    """
    esta_reservado = serializers.BooleanField(read_only=True)
    esta_disponible = serializers.BooleanField(read_only=True)
    ya_paso = serializers.BooleanField(read_only=True)
    fecha_hora_fin = serializers.DateTimeField(read_only=True)

    class Meta:
        model = PmDisponibilidad
        fields = [
            'id_disponibilidad', 'profesional', 'fecha_hora', 'fecha_hora_fin',
            'duracion_minutos', 'cita', 'estado', 'fecha_creacion',
            'esta_reservado', 'esta_disponible', 'ya_paso',
        ]
        read_only_fields = fields


class PmDisponibilidadPublicaSerializer(serializers.ModelSerializer):
    """
    Lo que ve el paciente al elegir una hora. Deliberadamente NO expone el
    campo 'cita': este listado solo entrega bloques libres, y filtrar el dato
    evita insinuar cuántos pacientes tiene agendados el profesional.
    """
    fecha_hora_fin = serializers.DateTimeField(read_only=True)

    class Meta:
        model = PmDisponibilidad
        fields = ['id_disponibilidad', 'profesional', 'fecha_hora', 'fecha_hora_fin', 'duracion_minutos']
        read_only_fields = fields


class PmDisponibilidadPublicarSerializer(serializers.Serializer):
    """
    Body de POST /api/pm/citas/disponibilidad/publicar/.
    Acepta varias horas de una vez para poder publicar una jornada completa
    sin repetir la petición por cada bloque.
    """
    fechas_hora = serializers.ListField(
        child=serializers.DateTimeField(),
        allow_empty=False,
        max_length=100,
    )
    duracion_minutos = serializers.IntegerField(
        required=False, min_value=DURACION_MINUTOS_MINIMA, max_value=DURACION_MINUTOS_MAXIMA
    )


class PmCitaPacienteInvitadoSerializer(serializers.Serializer):
    """
    Datos personales que debe entregar quien reserva SIN haber iniciado sesión.
    Son los mismos campos del registro salvo la contraseña: con ellos se crea
    (o se recupera) la ficha del paciente. Ver
    PmCliente_Queryset.obtener_o_crear_para_reserva.
    """
    nombres_cliente = serializers.CharField(max_length=100)
    apellidos_clientes = serializers.CharField(max_length=100)
    rut_cliente = serializers.CharField(max_length=12)
    fecha_nacimiento_cliente = serializers.DateField()
    email_cliente = serializers.EmailField()
    telefono_cliente = serializers.CharField(max_length=20)


class PmCitaReservarBloqueSerializer(serializers.Serializer):
    """
    Body de POST /api/pm/citas/reservar/.

    El paciente ya no propone fecha ni duración: elige uno de los bloques que
    el profesional publicó, y de ahí salen el horario, la duración y el propio
    profesional. Por eso el único identificador que viaja es el del bloque.

    'paciente' solo se envía cuando no hay sesión iniciada. Si el token de
    paciente está presente, se ignora: el dueño de la cita siempre sale del
    token, nunca del cuerpo.
    """
    # El queryset son solo los bloques reservables, así que una hora que acaba
    # de ser tomada por otra persona no se encuentra. El mensaje por defecto de
    # DRF para ese caso es 'Invalid pk "3" - object does not exist', que además
    # de estar en inglés no le dice nada a un paciente: se reemplaza.
    id_disponibilidad = serializers.PrimaryKeyRelatedField(
        queryset=PmDisponibilidad.objects.disponibles(),
        error_messages={
            'does_not_exist': (
                'Esa hora ya no está disponible. Puede que otra persona la haya '
                'tomado o que el profesional la haya retirado; vuelva a elegir.'
            ),
            'incorrect_type': 'Identificador de hora no válido.',
        },
    )
    motivo_consulta = serializers.CharField(required=False, allow_blank=True, default='')
    paciente = PmCitaPacienteInvitadoSerializer(required=False)
