from rest_framework import serializers

from PmCliente.models import PmCliente
from PmMedico.models import PM_Profesional
from PmCita.models import PmCita, DURACION_MINUTOS_MINIMA, DURACION_MINUTOS_MAXIMA


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

class PmCitaReservarSerializer(serializers.Serializer):
    """Body esperado por POST /api/pm/citas/reservar/."""
    id_cliente = serializers.PrimaryKeyRelatedField(queryset=PmCliente.objects.activos())
    id_profesional = serializers.PrimaryKeyRelatedField(queryset=PM_Profesional.objects.activos())
    fecha_hora = serializers.DateTimeField()
    motivo_consulta = serializers.CharField(required=False, allow_blank=True, default='')
    duracion_minutos = serializers.IntegerField(
        required=False, min_value=DURACION_MINUTOS_MINIMA, max_value=DURACION_MINUTOS_MAXIMA
    )


class PmCitaClienteCancelarSerializer(serializers.Serializer):
    """
    Body esperado al cancelar desde el lado del cliente. Como PmCliente
    todavía no tiene sesión propia (ver TODO en views.py), el frontend debe
    enviar el id_cliente dueño de la cita.
    """
    id_cliente = serializers.PrimaryKeyRelatedField(queryset=PmCliente.objects.activos())
    motivo = serializers.CharField(required=False, allow_blank=True, default='')


class PmCitaClientePosponerSerializer(serializers.Serializer):
    """Body esperado al posponer desde el lado del cliente."""
    id_cliente = serializers.PrimaryKeyRelatedField(queryset=PmCliente.objects.activos())
    fecha_hora = serializers.DateTimeField()
    motivo = serializers.CharField(required=False, allow_blank=True, default='')


class PmCitaCancelarSerializer(serializers.Serializer):
    """Body esperado al cancelar desde el lado del profesional (autenticado)."""
    motivo = serializers.CharField(required=False, allow_blank=True, default='')


class PmCitaPosponerSerializer(serializers.Serializer):
    """Body esperado al posponer desde el lado del profesional (autenticado)."""
    fecha_hora = serializers.DateTimeField()
    motivo = serializers.CharField(required=False, allow_blank=True, default='')
