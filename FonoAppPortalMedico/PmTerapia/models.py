import math
from datetime import timedelta

from django.db import models
from django.utils import timezone
from cloudinary.models import CloudinaryField

from PmMedico.models import PM_Profesional
from PmCliente.models import PmCliente
from PmCita.models import PmCita
from PmTerapia.queryset import PmEjercicio_Queryset, PmPlanTerapia_Queryset, PmVideoProgreso_Queryset
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
# tres tareas diarias no se cumplen.
EJERCICIOS_MAXIMOS_POR_PLAN = 3

# Video de progreso del paciente: mismos topes que el de síntomas (30 s, 50 MB),
# pero vive solo 7 días. Es material de trabajo que se revisa y se descarta.
PROGRESO_DURACION_MAXIMA_SEGUNDOS = 30
PROGRESO_TAMANO_MAXIMO_MB = 50
PROGRESO_DIAS_VIGENCIA = 7


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
        True si algún plan lo tiene asignado, activo o no: un ejercicio que
        salió de un plan sigue teniendo videos de progreso que lo referencian.
        """
        return self.asignaciones.exists()

    def eliminar_archivo_fisico(self):
        """Borra el video de ejemplo de Cloudinary. El registro no se toca."""
        if self.video_ejemplo:
            borrar_de_cloudinary(self.video_ejemplo)

    def __str__(self):
        return f'{self.nombre} ({self.profesional})'


class PmPlanTerapia(models.Model):
    """
    El plan de terapia de un paciente con un fonoaudiólogo.

    Se crea desde una cita realizada: tras reunirse, el fonoaudiólogo le asigna
    hasta 3 ejercicios de su catálogo y le indica cada cuánto debe reportar con
    un video. Un paciente tiene como máximo UN plan activo con cada fonoaudiólogo;
    en citas siguientes el mismo plan se ajusta, así que el historial de videos
    y retroalimentaciones es continuo.

    Los periodos no se guardan: se calculan desde 'fecha_inicio' y la
    periodicidad (ver periodos.py), en hora de Chile.
    """

    class Periodicidad(models.TextChoices):
        DIARIA = 'DIARIA', 'Diaria'
        SEMANAL = 'SEMANAL', 'Semanal'
        QUINCENAL = 'QUINCENAL', 'Quincenal'

    class Estado(models.TextChoices):
        ACTIVO = 'ACTIVO', 'Activo'
        CERRADO = 'CERRADO', 'Cerrado'

    id_plan = models.AutoField('Código del plan', primary_key=True)

    cliente = models.ForeignKey(
        PmCliente, on_delete=models.CASCADE, related_name='planes_terapia',
        verbose_name='Paciente',
    )
    profesional = models.ForeignKey(
        PM_Profesional, on_delete=models.CASCADE, related_name='planes_terapia',
        verbose_name='Fonoaudiólogo',
    )
    # La cita realizada desde la que se creó. SET_NULL por si alguna vez se
    # borrara una cita: el plan y su historial no deben irse con ella.
    cita_origen = models.ForeignKey(
        PmCita, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='planes_terapia', verbose_name='Cita desde la que se creó',
    )

    periodicidad = models.CharField(max_length=10, choices=Periodicidad.choices)
    # Fecha (no datetime) en Chile: el día cero del cálculo de periodos.
    fecha_inicio = models.DateField(verbose_name='Primer día del plan')
    indicaciones = models.TextField(blank=True, default='', verbose_name='Indicaciones generales')

    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)

    # Hasta qué periodo ya se envió recordatorio. -1 = ninguno todavía. Lo usa
    # el comando diario para no avisar dos veces por el mismo periodo.
    ultimo_periodo_recordado = models.IntegerField(default=-1)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    objects = PmPlanTerapia_Queryset.as_manager()

    class Meta:
        verbose_name = 'Plan de terapia'
        verbose_name_plural = 'Planes de terapia'
        ordering = ['-fecha_creacion']
        # "Un solo plan ACTIVO por par paciente–fonoaudiólogo" NO va como
        # UniqueConstraint con condición: MariaDB no soporta índices parciales
        # y Django la omite en silencio (aviso models.W036), con lo que el
        # modelo prometería algo que la base no cumple. La regla se aplica en
        # PmPlanTerapia_Queryset.crear(), dentro de una transacción. Los planes
        # cerrados pueden acumularse: son el historial.

    @property
    def esta_activo(self):
        return self.estado == self.Estado.ACTIVO

    def ejercicios_activos(self):
        """Los ejercicios que hoy forman parte del plan, en su orden."""
        return self.asignaciones.filter(estado=True).select_related('ejercicio').order_by('orden')

    def __str__(self):
        return f'Plan de {self.cliente} con {self.profesional} ({self.get_periodicidad_display()})'


class PmPlanEjercicio(models.Model):
    """
    Un ejercicio dentro de un plan, con su orden e indicaciones propias.

    Al ajustar el plan, los ejercicios que salen se DESACTIVAN en vez de
    borrarse: sus videos de progreso anteriores deben seguir teniendo dueño. Si
    el fonoaudiólogo vuelve a asignar uno que había quitado, se reactiva la
    misma fila; por eso la unicidad (plan, ejercicio) no estorba.
    """

    id_plan_ejercicio = models.AutoField('Código', primary_key=True)

    plan = models.ForeignKey(PmPlanTerapia, on_delete=models.CASCADE, related_name='asignaciones')
    # related_name='asignaciones' es lo que lee PmEjercicio.esta_en_uso().
    ejercicio = models.ForeignKey(PmEjercicio, on_delete=models.PROTECT, related_name='asignaciones')

    orden = models.PositiveSmallIntegerField(verbose_name='Orden en el plan (1 a 3)')
    indicaciones = models.TextField(blank=True, default='', verbose_name='Indicaciones para este paciente')

    estado = models.BooleanField(default=True, verbose_name='Forma parte del plan hoy')

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ejercicio del plan'
        verbose_name_plural = 'Ejercicios del plan'
        ordering = ['orden']
        constraints = [
            models.UniqueConstraint(fields=['plan', 'ejercicio'], name='pmterapia_ejercicio_unico_por_plan'),
        ]

    def __str__(self):
        return f'{self.orden}. {self.ejercicio.nombre}'


class PmVideoProgreso(models.Model):
    """
    Un video del paciente practicando uno de los ejercicios de su plan.

    Vive 7 días: es material de trabajo, no clínico de largo plazo, y con
    reportes diarios o semanales se acumularía sin sentido. Al vencer se borra
    el archivo y el registro queda: el paciente sigue viendo la fecha y la
    retroalimentación que le dejaron, aunque el video ya no esté.

    'numero_periodo' se calcula al subir (en hora de Chile, ver periodos.py) y
    se guarda para no recalcularlo en cada lectura. Es lo que decide si el
    periodo quedó cumplido.
    """

    class MotivoEliminacion(models.TextChoices):
        VENCIMIENTO = 'VE', 'Vencimiento de los 7 días'
        RETIRO_PACIENTE = 'RP', 'Retirado por el propio paciente'
        ORDEN_MEDICA = 'OM', 'Eliminado por orden del fonoaudiólogo'

    id_video = models.AutoField('Código del video', primary_key=True)

    plan_ejercicio = models.ForeignKey(
        PmPlanEjercicio, on_delete=models.CASCADE, related_name='videos',
        verbose_name='Ejercicio del plan al que responde',
    )

    video = CloudinaryField('video', folder='pm/videos/progreso/', resource_type='video')
    duracion_segundos = models.PositiveIntegerField(verbose_name='Duración en segundos')
    comentario = models.TextField(blank=True, default='', verbose_name='Comentario del paciente')

    fecha_subida = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField(verbose_name='Fecha en que deja de estar disponible')
    numero_periodo = models.IntegerField(verbose_name='Periodo del plan al que pertenece')

    # Retroalimentación del fonoaudiólogo (entrega de seguimiento). Nula hasta
    # que la escriba; sobrevive al vencimiento del archivo.
    retroalimentacion = models.TextField(null=True, blank=True)
    fecha_retroalimentacion = models.DateTimeField(null=True, blank=True)

    # Control y trazabilidad, como en PmVideo
    estado = models.BooleanField(default=True, verbose_name='Disponible')
    fecha_eliminacion = models.DateTimeField(null=True, blank=True)
    motivo_eliminacion = models.CharField(max_length=2, choices=MotivoEliminacion.choices, null=True, blank=True)

    objects = PmVideoProgreso_Queryset.as_manager()

    class Meta:
        verbose_name = 'Video de progreso'
        verbose_name_plural = 'Videos de progreso'
        ordering = ['-fecha_subida']

    def save(self, *args, **kwargs):
        if not self.fecha_expiracion:
            self.fecha_expiracion = timezone.now() + timedelta(days=PROGRESO_DIAS_VIGENCIA)
        super().save(*args, **kwargs)

    @property
    def esta_vigente(self):
        return self.estado and self.fecha_expiracion > timezone.now()

    @property
    def dias_restantes(self):
        """Redondeado hacia arriba: recién subido muestra 7, no 6."""
        if not self.estado:
            return 0
        segundos = (self.fecha_expiracion - timezone.now()).total_seconds()
        return max(math.ceil(segundos / 86400), 0)

    @property
    def tiene_retroalimentacion(self):
        return bool(self.retroalimentacion)

    def eliminar_archivo_fisico(self):
        """Borra el archivo de Cloudinary; el registro no se toca."""
        if self.video:
            borrar_de_cloudinary(self.video)

    def __str__(self):
        return f'Video #{self.id_video} de {self.plan_ejercicio}'
