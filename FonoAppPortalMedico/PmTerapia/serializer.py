from rest_framework import serializers

from Security.archivos import url_absoluta
from Security.validacion_video import validar_archivo, validar_duracion
from PmTerapia.models import (
    PmEjercicio,
    PmPlanTerapia,
    PmPlanEjercicio,
    EJEMPLO_DURACION_MAXIMA_SEGUNDOS,
    EJEMPLO_TAMANO_MAXIMO_MB,
    EJERCICIOS_MAXIMOS_POR_PLAN,
)
from PmTerapia.periodos import periodo_actual, rango_de_periodo


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


# ==========================================================================
# PLAN DE TERAPIA
# ==========================================================================

class PmPlanEjercicioSerializer(serializers.ModelSerializer):
    """
    Un ejercicio dentro del plan, con el ejercicio del catálogo incrustado:
    quien lee el plan (fonoaudiólogo o paciente) necesita el nombre, las
    instrucciones y el video de ejemplo sin hacer otra llamada.
    """
    ejercicio = PmEjercicioSerializer(read_only=True)

    class Meta:
        model = PmPlanEjercicio
        fields = ['id_plan_ejercicio', 'orden', 'indicaciones', 'ejercicio']
        read_only_fields = fields


class PmPlanTerapiaSerializer(serializers.ModelSerializer):
    """
    El plan, para ambos lados. Trae los ejercicios activos incrustados, los
    nombres del paciente y del fonoaudiólogo (cada lado usa el que le falta) y
    el periodo actual ya calculado, para que ninguna pantalla tenga que
    reproducir la aritmética de fechas.
    """
    ejercicios = serializers.SerializerMethodField()
    paciente_nombre = serializers.SerializerMethodField()
    profesional_nombre = serializers.SerializerMethodField()
    periodicidad_display = serializers.CharField(source='get_periodicidad_display', read_only=True)
    periodo_actual = serializers.SerializerMethodField()
    esta_activo = serializers.BooleanField(read_only=True)

    class Meta:
        model = PmPlanTerapia
        fields = [
            'id_plan', 'cliente', 'profesional', 'cita_origen',
            'paciente_nombre', 'profesional_nombre',
            'periodicidad', 'periodicidad_display', 'fecha_inicio', 'indicaciones',
            'estado', 'esta_activo', 'periodo_actual',
            'ejercicios',
            'fecha_creacion', 'fecha_actualizacion', 'fecha_cierre',
        ]
        read_only_fields = fields

    def get_ejercicios(self, plan):
        return PmPlanEjercicioSerializer(plan.ejercicios_activos(), many=True).data

    def get_paciente_nombre(self, plan):
        return f'{plan.cliente.nombres_cliente} {plan.cliente.apellidos_clientes}'

    def get_profesional_nombre(self, plan):
        return f'{plan.profesional.nombres_profesional} {plan.profesional.apellidos_profesional}'

    def get_periodo_actual(self, plan):
        """Número del periodo en curso y sus fechas, en hora de Chile."""
        numero = periodo_actual(plan.fecha_inicio, plan.periodicidad)
        primero, ultimo = rango_de_periodo(plan.fecha_inicio, plan.periodicidad, numero)
        return {'numero': numero, 'desde': primero.isoformat(), 'hasta': ultimo.isoformat()}


class PmPlanEjercicioEntradaSerializer(serializers.Serializer):
    """Un ejercicio tal como llega al crear o ajustar: su id y las indicaciones."""
    id_ejercicio = serializers.IntegerField()
    indicaciones = serializers.CharField(required=False, allow_blank=True, default='')


class PmPlanTerapiaEntradaSerializer(serializers.Serializer):
    """
    Cuerpo de crear y de ajustar un plan.

    Valida lo que no depende de la base: entre 1 y EJERCICIOS_MAXIMOS_POR_PLAN
    ejercicios, sin repetidos, y que todos sean del fonoaudiólogo (eso sí
    consulta, pero es parte de "estos datos son válidos para ti"). Deja
    'ejercicios' resuelto a instancias para que el queryset no vuelva a buscar.
    """
    id_cita = serializers.IntegerField(required=False)
    periodicidad = serializers.ChoiceField(choices=PmPlanTerapia.Periodicidad.choices, required=False)
    indicaciones = serializers.CharField(required=False, allow_blank=True)
    ejercicios = PmPlanEjercicioEntradaSerializer(many=True, required=False)

    def validate_ejercicios(self, items):
        if not 1 <= len(items) <= EJERCICIOS_MAXIMOS_POR_PLAN:
            raise serializers.ValidationError(
                f'Asigna entre 1 y {EJERCICIOS_MAXIMOS_POR_PLAN} ejercicios.'
            )

        ids = [item['id_ejercicio'] for item in items]
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError('Hay un ejercicio repetido.')

        profesional = self.context['profesional']
        encontrados = {
            e.pk: e for e in PmEjercicio.objects.de_profesional(profesional.pk).filter(pk__in=ids)
        }
        faltan = [i for i in ids if i not in encontrados]
        if faltan:
            raise serializers.ValidationError('Alguno de los ejercicios no existe o no está en tu catálogo.')

        return [
            {'ejercicio': encontrados[item['id_ejercicio']], 'indicaciones': item.get('indicaciones', '')}
            for item in items
        ]
