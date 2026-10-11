from rest_framework import serializers

from Security.archivos import url_absoluta
from Security.validacion_video import validar_archivo, validar_duracion
from PmTerapia.models import (
    PmEjercicio,
    PmPlanTerapia,
    PmPlanEjercicio,
    PmVideoProgreso,
    EJEMPLO_DURACION_MAXIMA_SEGUNDOS,
    EJEMPLO_TAMANO_MAXIMO_MB,
    EJERCICIOS_MAXIMOS_POR_PLAN,
    PROGRESO_DURACION_MAXIMA_SEGUNDOS,
    PROGRESO_TAMANO_MAXIMO_MB,
)
from PmTerapia.periodos import periodo_actual, rango_de_periodo
from PmTerapia.queryset import cumplimiento_de


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

    'enviado_periodo_actual' es lo que la pantalla del paciente muestra como
    "enviado" o "falta". Se calcula con el periodo actual que llega por
    contexto desde el serializer del plan, para no repetir la aritmética.
    """
    ejercicio = PmEjercicioSerializer(read_only=True)
    enviado_periodo_actual = serializers.SerializerMethodField()

    class Meta:
        model = PmPlanEjercicio
        fields = ['id_plan_ejercicio', 'orden', 'indicaciones', 'ejercicio', 'enviado_periodo_actual']
        read_only_fields = fields

    def get_enviado_periodo_actual(self, asignacion):
        periodo = self.context.get('periodo_actual')
        if periodo is None:
            return False
        # Cuenta también el que ya venció: se envió, y eso es lo que importa.
        return asignacion.videos.que_cuentan().filter(numero_periodo=periodo).exists()


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
    # Semáforo del seguimiento: al día / atrasado, y cuándo fue el último video.
    al_dia = serializers.SerializerMethodField()
    ultimo_video = serializers.SerializerMethodField()

    class Meta:
        model = PmPlanTerapia
        fields = [
            'id_plan', 'cliente', 'profesional', 'cita_origen',
            'paciente_nombre', 'profesional_nombre',
            'periodicidad', 'periodicidad_display', 'fecha_inicio', 'indicaciones',
            'estado', 'esta_activo', 'periodo_actual',
            'al_dia', 'ultimo_video',
            'ejercicios',
            'fecha_creacion', 'fecha_actualizacion', 'fecha_cierre',
        ]
        read_only_fields = fields

    def _cumplimiento(self, plan):
        # Se calcula una vez por plan aunque lo pidan varios campos.
        cache = self.context.setdefault('_cumplimiento', {})
        if plan.pk not in cache:
            cache[plan.pk] = cumplimiento_de(plan)
        return cache[plan.pk]

    def get_al_dia(self, plan):
        return self._cumplimiento(plan)['al_dia']

    def get_ultimo_video(self, plan):
        fecha = self._cumplimiento(plan)['ultimo_video']
        return fecha.isoformat() if fecha else None

    def get_ejercicios(self, plan):
        return PmPlanEjercicioSerializer(
            plan.ejercicios_activos(), many=True,
            context={'periodo_actual': periodo_actual(plan.fecha_inicio, plan.periodicidad)},
        ).data

    def get_paciente_nombre(self, plan):
        return f'{plan.cliente.nombres_cliente} {plan.cliente.apellidos_clientes}'

    def get_profesional_nombre(self, plan):
        return f'{plan.profesional.nombres_profesional} {plan.profesional.apellidos_profesional}'

    def get_periodo_actual(self, plan):
        """Número del periodo en curso y sus fechas, en hora de Chile."""
        numero = periodo_actual(plan.fecha_inicio, plan.periodicidad)
        primero, ultimo = rango_de_periodo(plan.fecha_inicio, plan.periodicidad, numero)
        return {'numero': numero, 'desde': primero.isoformat(), 'hasta': ultimo.isoformat()}


class PmPlanTerapiaSeguimientoSerializer(PmPlanTerapiaSerializer):
    """
    El plan como lo ve el fonoaudiólogo en el detalle del seguimiento: lo mismo
    que el plan, más los periodos ya cerrados con qué ejercicios faltaron en
    cada uno. El historial de videos va por su propio endpoint.
    """
    periodos_cerrados = serializers.SerializerMethodField()

    class Meta(PmPlanTerapiaSerializer.Meta):
        fields = PmPlanTerapiaSerializer.Meta.fields + ['periodos_cerrados']
        read_only_fields = fields

    def get_periodos_cerrados(self, plan):
        return self._cumplimiento(plan)['periodos_cerrados']


class PmRetroalimentacionSerializer(serializers.Serializer):
    """Lo que escribe el fonoaudiólogo sobre un video. Vacío = borrar la retroalimentación."""
    retroalimentacion = serializers.CharField(allow_blank=True, max_length=4000)


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


# ==========================================================================
# VIDEO DE PROGRESO
# ==========================================================================

class PmVideoProgresoSerializer(serializers.ModelSerializer):
    """
    Un video de progreso, para el paciente y para el fonoaudiólogo.

    'video' llega como URL, o null si el archivo ya venció: el registro sigue
    valiendo por su fecha y su retroalimentación. Incluye el nombre del
    ejercicio y el id de su asignación para que el historial se pueda leer y
    agrupar sin otra llamada.
    """
    dias_restantes = serializers.IntegerField(read_only=True)
    esta_vigente = serializers.BooleanField(read_only=True)
    tiene_retroalimentacion = serializers.BooleanField(read_only=True)
    ejercicio_nombre = serializers.CharField(source='plan_ejercicio.ejercicio.nombre', read_only=True)

    class Meta:
        model = PmVideoProgreso
        fields = [
            'id_video', 'plan_ejercicio', 'ejercicio_nombre',
            'video', 'duracion_segundos', 'comentario',
            'fecha_subida', 'fecha_expiracion', 'numero_periodo',
            'retroalimentacion', 'fecha_retroalimentacion', 'tiene_retroalimentacion',
            'estado', 'dias_restantes', 'esta_vigente',
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        datos = super().to_representation(instance)
        # Vencido o retirado: el archivo ya no está, y una URL a algo borrado
        # solo produce un reproductor roto.
        datos['video'] = url_absoluta(instance.video) if instance.esta_vigente else None
        return datos


class PmVideoProgresoSubirSerializer(serializers.Serializer):
    """
    Lo que llega al subir: el archivo, su duración declarada, el ejercicio del
    plan al que responde y un comentario opcional. El dueño, el plan y el
    periodo los pone la vista; nada de eso se acepta desde el cuerpo.
    """
    id_plan_ejercicio = serializers.IntegerField()
    video = serializers.FileField()
    duracion_segundos = serializers.IntegerField()
    comentario = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_video(self, archivo):
        return validar_archivo(archivo, PROGRESO_TAMANO_MAXIMO_MB)

    def validate_duracion_segundos(self, value):
        return validar_duracion(value, PROGRESO_DURACION_MAXIMA_SEGUNDOS)
