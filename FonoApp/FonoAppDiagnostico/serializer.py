from rest_framework import serializers
from FonoAppDiagnostico.models import (
    FonoApp_Diagnostico_Formulario,
    FonoApp_Diagnostico_Subescala,
    FonoApp_Diagnostico_Pregunta,
    FonoApp_Diagnostico_Interpretacion,
    FonoApp_Diagnostico_Respuesta,
)


def _validar_rangos_sin_solape(rangos, contexto):
    """Verifica que una lista de rangos {valor_minimo, valor_maximo} no se solape entre sí.

    Se usa tanto para los rangos del puntaje total como para los de cada subescala
    (ambos son listas independientes de FonoApp_Diagnostico_Interpretacion).
    """
    ordenados = sorted(rangos, key=lambda rango: rango['valor_minimo'])
    for anterior, actual in zip(ordenados, ordenados[1:]):
        if actual['valor_minimo'] <= anterior['valor_maximo']:
            raise serializers.ValidationError(
                f'Los rangos de interpretación de {contexto} se solapan: '
                f'{anterior["valor_minimo"]}-{anterior["valor_maximo"]} y '
                f'{actual["valor_minimo"]}-{actual["valor_maximo"]}.'
            )


# =============================================================================
# FORMULARIO (plantilla del test): creación anidada de subescalas + preguntas
# + interpretaciones (rangos de puntaje -> resultado clínico)
# =============================================================================

class FonoApp_Diagnostico_PreguntaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FonoApp_Diagnostico_Pregunta
        fields = ['id_pregunta', 'texto', 'orden']
        read_only_fields = ['id_pregunta']


class FonoApp_Diagnostico_InterpretacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FonoApp_Diagnostico_Interpretacion
        fields = ['id_interpretacion', 'valor_minimo', 'valor_maximo', 'etiqueta', 'descripcion']
        read_only_fields = ['id_interpretacion']

    def validate(self, data):
        if data['valor_maximo'] < data['valor_minimo']:
            raise serializers.ValidationError(
                'El valor máximo del rango debe ser mayor o igual al valor mínimo.'
            )
        return data


class FonoApp_Diagnostico_SubescalaSerializer(serializers.ModelSerializer):
    preguntas = FonoApp_Diagnostico_PreguntaSerializer(many=True)
    interpretaciones = FonoApp_Diagnostico_InterpretacionSerializer(many=True, required=False)

    class Meta:
        model = FonoApp_Diagnostico_Subescala
        fields = ['id_subescala', 'nombre', 'orden', 'preguntas', 'interpretaciones']
        read_only_fields = ['id_subescala']

    def validate_preguntas(self, preguntas):
        if not preguntas:
            raise serializers.ValidationError('Cada subescala debe tener al menos una pregunta.')
        return preguntas

    def validate(self, data):
        interpretaciones = data.get('interpretaciones') or []
        if interpretaciones:
            _validar_rangos_sin_solape(interpretaciones, f'la subescala "{data.get("nombre")}"')
        return data


class FonoApp_Diagnostico_FormularioSerializer(serializers.ModelSerializer):
    subescalas = FonoApp_Diagnostico_SubescalaSerializer(many=True)
    interpretaciones = FonoApp_Diagnostico_InterpretacionSerializer(many=True, required=False)

    class Meta:
        model = FonoApp_Diagnostico_Formulario
        fields = [
            'id_formulario', 'nombre', 'descripcion', 'valor_minimo', 'valor_maximo',
            'estado', 'fecha_creacion', 'FonoApp_Administracion', 'subescalas', 'interpretaciones',
        ]
        read_only_fields = ['id_formulario', 'estado', 'fecha_creacion', 'FonoApp_Administracion']

    def validate(self, data):
        if data['valor_maximo'] <= data['valor_minimo']:
            raise serializers.ValidationError(
                'El valor máximo de la escala debe ser mayor al valor mínimo.'
            )
        if not data.get('subescalas'):
            raise serializers.ValidationError(
                'El formulario debe tener al menos una subescala con preguntas.'
            )

        interpretaciones_total = data.get('interpretaciones') or []
        if interpretaciones_total:
            _validar_rangos_sin_solape(interpretaciones_total, 'el puntaje total')

        return data

    def create(self, validated_data):
        subescalas_data = validated_data.pop('subescalas')
        interpretaciones_data = validated_data.pop('interpretaciones', [])
        usuario = self.context['request'].user
        return FonoApp_Diagnostico_Formulario.objects.crear_formulario(
            usuario=usuario, subescalas_data=subescalas_data,
            interpretaciones_data=interpretaciones_data, **validated_data
        )

    def to_representation(self, instance):
        # 'instance.interpretaciones' trae TODOS los rangos del formulario (los del
        # puntaje total y los de cada subescala, comparten la misma FK 'formulario').
        # Acá el campo de nivel formulario debe mostrar solo los del puntaje total;
        # los de cada subescala ya se listan dentro de su propio 'subescalas[].interpretaciones'.
        data = super().to_representation(instance)
        data['interpretaciones'] = FonoApp_Diagnostico_InterpretacionSerializer(
            instance.interpretaciones.filter(subescala__isnull=True), many=True
        ).data
        return data


# =============================================================================
# RESPUESTA (aplicación del test a un paciente) y cálculo del resultado
# =============================================================================

class FonoApp_Diagnostico_RespuestaDetalleInputSerializer(serializers.Serializer):
    pregunta = serializers.PrimaryKeyRelatedField(queryset=FonoApp_Diagnostico_Pregunta.objects.all())
    valor = serializers.IntegerField()


class FonoApp_Diagnostico_RespuestaSerializer(serializers.ModelSerializer):
    detalles = FonoApp_Diagnostico_RespuestaDetalleInputSerializer(many=True, write_only=True)
    resultado = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FonoApp_Diagnostico_Respuesta
        fields = [
            'id_respuesta', 'formulario', 'paciente_nombre', 'paciente_fecha_nacimiento',
            'fecha_diligenciamiento', 'FonoApp_Administracion', 'detalles', 'resultado',
        ]
        read_only_fields = [
            'id_respuesta', 'fecha_diligenciamiento', 'FonoApp_Administracion',
        ]

    def get_resultado(self, obj):
        """Puntaje total (con su interpretación, si el formulario tiene rangos definidos)
        y desglose por subescala (ej. Parte 1/2/3 del IFV, o Funcional/Física/Emocional
        del IDV-CH, cada una con su propia interpretación), ya calculado al registrar
        la respuesta."""
        return {
            'puntaje_total': obj.puntaje_total,
            'interpretacion_total': obj.interpretacion_total,
            'subescalas': obj.detalle_subescalas,
        }

    def validate(self, data):
        formulario = data['formulario']
        if not formulario.estado:
            raise serializers.ValidationError('El formulario indicado no está activo.')

        detalles = data.get('detalles') or []
        if not detalles:
            raise serializers.ValidationError('Debe enviar las respuestas del test (detalles).')

        preguntas_formulario = set(
            formulario.preguntas.values_list('id_pregunta', flat=True)
        )
        preguntas_enviadas = set()

        for detalle in detalles:
            pregunta = detalle['pregunta']
            valor = detalle['valor']

            if pregunta.formulario_id != formulario.id_formulario:
                raise serializers.ValidationError(
                    f'La pregunta {pregunta.id_pregunta} no pertenece al formulario indicado.'
                )
            if not (formulario.valor_minimo <= valor <= formulario.valor_maximo):
                raise serializers.ValidationError(
                    f'El valor de la pregunta {pregunta.id_pregunta} debe estar entre '
                    f'{formulario.valor_minimo} y {formulario.valor_maximo}.'
                )
            if pregunta.id_pregunta in preguntas_enviadas:
                raise serializers.ValidationError(
                    f'La pregunta {pregunta.id_pregunta} fue respondida más de una vez.'
                )
            preguntas_enviadas.add(pregunta.id_pregunta)

        faltantes = preguntas_formulario - preguntas_enviadas
        if faltantes:
            raise serializers.ValidationError(
                f'Faltan respuestas para las preguntas: {sorted(faltantes)}'
            )

        return data

    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles')
        usuario = self.context['request'].user
        # El endpoint es público (el cliente responde sin cuenta propia): si no
        # viene un token válido, 'usuario' es AnonymousUser y se guarda como None.
        usuario = usuario if usuario and usuario.is_authenticated else None
        return FonoApp_Diagnostico_Respuesta.objects.registrar_respuesta(
            usuario=usuario, detalles_data=detalles_data, **validated_data
        )


class FonoApp_Diagnostico_RespuestaListadoSerializer(serializers.ModelSerializer):
    """Versión liviana usada para listar resultados ya registrados de un formulario."""

    class Meta:
        model = FonoApp_Diagnostico_Respuesta
        fields = [
            'id_respuesta', 'formulario', 'paciente_nombre', 'paciente_fecha_nacimiento',
            'fecha_diligenciamiento', 'puntaje_total', 'interpretacion_total', 'detalle_subescalas',
        ]


class FonoApp_Diagnostico_EnviarCorreoSerializer(serializers.Serializer):
    """Solo valida el formato del correo que el paciente escribe al ver su resultado.

    No es un ModelSerializer a propósito: el correo no se guarda en ningún modelo,
    solo se usa para el envío en curso (ver FonoAppDiagnostico/correos.py).
    """
    correo = serializers.EmailField()
