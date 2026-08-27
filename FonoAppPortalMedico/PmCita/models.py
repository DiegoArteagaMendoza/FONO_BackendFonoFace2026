from datetime import timedelta

from django.db import models
from django.utils import timezone

from PmCliente.models import PmCliente
from PmMedico.models import PM_Profesional
from PmCita.queryset import PmCita_Queryset, PmDisponibilidad_Queryset

# ==========================================================================
# REGLAS DEL NEGOCIO (centralizadas para no repetirlas en el código)
# ==========================================================================

# Duración de la cita si el cliente no indica otra al reservar
DURACION_MINUTOS_DEFECTO = 45

# Rango aceptado para la duración, tanto al reservar como al reprogramar
DURACION_MINUTOS_MINIMA = 15
DURACION_MINUTOS_MAXIMA = 120

# No se puede reservar, cancelar ni reprogramar una cita a menos de esta
# cantidad de horas de anticipación respecto de la hora agendada (evita
# cambios de último minuto que dejan al otro lado sin aviso razonable).
HORAS_MINIMAS_ANTICIPACION = 2

# Tope de reprogramaciones por cita: agotado el cupo, hay que cancelar y
# reservar una nueva (evita que una misma cita se arrastre indefinidamente).
REPROGRAMACIONES_MAXIMAS = 3

# Código de seguimiento que se envía por correo al reservar. Es la única forma
# que tiene de gestionar su hora quien reservó sin cuenta, así que funciona como
# credencial: debe ser imposible de adivinar probando.
#
# El alfabeto excluye 0/O y 1/I/L, que se confunden al leerlos de un correo y
# teclearlos. Con 8 caracteres sobre 31 símbolos hay ~8.5·10^11 combinaciones.
LONGITUD_CODIGO_SEGUIMIENTO = 8
ALFABETO_CODIGO_SEGUIMIENTO = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'


def generar_codigo_seguimiento():
    """
    Código aleatorio para el seguimiento de una cita.

    Usa secrets y no random: random es predecible a partir de valores previos, y
    aquí el código da acceso a los datos de una cita.
    """
    import secrets

    return ''.join(
        secrets.choice(ALFABETO_CODIGO_SEGUIMIENTO)
        for _ in range(LONGITUD_CODIGO_SEGUIMIENTO)
    )


class PmCita(models.Model):
    """
    Cita médica telemática reservada por un PmCliente con un PM_Profesional
    (fonoaudiólogo ya acreditado).

    El cliente puede cancelarla (no la realizará) o posponerla a una nueva
    fecha/hora; el profesional puede hacer lo mismo desde su lado. Mientras
    sigue RESERVADA, el cliente puede adjuntar un video de síntomas (ver
    PmVideo.models.PmVideo.cita) que el profesional revisa antes o durante
    la atención.
    """

    class Estado(models.TextChoices):
        RESERVADA = 'RE', 'Reservada'
        CANCELADA_CLIENTE = 'CC', 'Cancelada por el cliente'
        CANCELADA_MEDICO = 'CM', 'Cancelada por el profesional'
        REALIZADA = 'RZ', 'Realizada'

    class Origen(models.TextChoices):
        CLIENTE = 'CLIENTE', 'Cliente'
        PROFESIONAL = 'PROFESIONAL', 'Profesional'

    id_cita = models.AutoField('Código cita', primary_key=True)

    cliente = models.ForeignKey(
        PmCliente,
        on_delete=models.CASCADE,
        related_name='citas',
        verbose_name='Cliente que reserva',
    )
    profesional = models.ForeignKey(
        PM_Profesional,
        on_delete=models.CASCADE,
        related_name='citas',
        verbose_name='Profesional que atiende',
    )

    # Código que se envía por correo al reservar. Lo tienen todas las citas, no
    # solo las de invitados: así el correo de confirmación es el mismo para
    # todos y quien tiene cuenta también puede consultar su hora sin entrar.
    codigo_seguimiento = models.CharField(
        max_length=LONGITUD_CODIGO_SEGUIMIENTO,
        unique=True,
        editable=False,
        verbose_name='Código de seguimiento',
    )

    fecha_hora = models.DateTimeField(verbose_name='Fecha y hora agendada')
    duracion_minutos = models.PositiveIntegerField(default=DURACION_MINUTOS_DEFECTO)
    motivo_consulta = models.TextField(blank=True, null=True, verbose_name='Motivo de la consulta')

    estado = models.CharField(max_length=2, choices=Estado.choices, default=Estado.RESERVADA)
    permite_carga_video = models.BooleanField(default=True, verbose_name='Permite adjuntar video de síntomas')

    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    # --- Cancelación ---
    motivo_cancelacion = models.TextField(blank=True, null=True)
    fecha_cancelacion = models.DateTimeField(null=True, blank=True)
    cancelada_por = models.CharField(max_length=12, choices=Origen.choices, null=True, blank=True)

    # --- Reprogramación (se conserva la fecha original y la última reprogramación;
    #     el conteo en veces_reprogramada guarda cuántas veces ya se movió) ---
    fecha_hora_original = models.DateTimeField(
        null=True, blank=True, verbose_name='Fecha y hora original, antes de la primera reprogramación'
    )
    veces_reprogramada = models.PositiveIntegerField(default=0)
    motivo_reprogramacion = models.TextField(blank=True, null=True, verbose_name='Motivo de la última reprogramación')
    reprogramada_por = models.CharField(max_length=12, choices=Origen.choices, null=True, blank=True)
    fecha_ultima_reprogramacion = models.DateTimeField(null=True, blank=True)

    # --- Atención ---
    fecha_marcada_realizada = models.DateTimeField(null=True, blank=True)

    objects = PmCita_Queryset.as_manager()

    class Meta:
        db_table = 'PmCita'
        managed = True
        verbose_name = 'Cita médica'
        verbose_name_plural = 'Citas médicas'
        ordering = ['-fecha_hora']

    def save(self, *args, **kwargs):
        # El código se asigna una sola vez, al crear: si cambiara, el enlace del
        # correo que ya recibió la persona dejaría de servir.
        if not self.codigo_seguimiento:
            self.codigo_seguimiento = self._codigo_unico()
        super().save(*args, **kwargs)

    @classmethod
    def _codigo_unico(cls, intentos=8):
        """
        Código libre. La probabilidad de choque es ínfima, pero comprobarlo sale
        gratis y una colisión rompería el guardado con un error de unicidad que
        nadie sabría interpretar.
        """
        for _ in range(intentos):
            codigo = generar_codigo_seguimiento()
            if not cls.objects.filter(codigo_seguimiento=codigo).exists():
                return codigo
        raise RuntimeError('No se pudo generar un código de seguimiento único.')

    def __str__(self):
        return f'Cita #{self.id_cita} - {self.cliente} con {self.profesional} ({self.get_estado_display()})'

    @property
    def esta_activa(self):
        """True si la cita sigue reservada (no fue cancelada ni ya se realizó)."""
        return self.estado == self.Estado.RESERVADA

    @property
    def ya_paso(self):
        """True si la fecha/hora agendada ya quedó en el pasado."""
        return self.fecha_hora < timezone.now()

    @property
    def hora_limite_cambio(self):
        """Desde esta hora en adelante ya no se admite cancelar ni reprogramar."""
        return self.fecha_hora - timedelta(hours=HORAS_MINIMAS_ANTICIPACION)

    def permite_cambios(self):
        """True si aún se puede cancelar o reprogramar (activa y fuera del margen mínimo)."""
        return self.esta_activa and timezone.now() < self.hora_limite_cambio


class PmDisponibilidad(models.Model):
    """
    Bloque horario que un profesional publica como disponible para atender.

    El paciente ya no propone una hora cualquiera: elige uno de estos bloques,
    y al reservarlo la cita queda ligada a él (ver el campo `cita`). Mientras
    `cita` sea nulo el bloque sigue libre; cuando la cita se cancela, el bloque
    se libera y vuelve a ofrecerse, porque esa hora del profesional quedó
    efectivamente disponible otra vez.

    Vive en la app PmCita, y no en una propia, porque no tiene sentido por
    separado: existe para ser consumido por una cita, y las reglas de duración
    y anticipación son las mismas que ya define este módulo.
    """

    id_disponibilidad = models.AutoField('Código disponibilidad', primary_key=True)

    profesional = models.ForeignKey(
        PM_Profesional,
        on_delete=models.CASCADE,
        related_name='disponibilidades',
        verbose_name='Profesional que ofrece la hora',
    )

    fecha_hora = models.DateTimeField(verbose_name='Inicio del bloque')
    duracion_minutos = models.PositiveIntegerField(default=DURACION_MINUTOS_DEFECTO)

    # Cita que ocupó este bloque. Nulo = sigue libre. SET_NULL en vez de CASCADE
    # a propósito: si algún día se borrara la cita, el bloque debe sobrevivir
    # liberado, no desaparecer junto con ella.
    cita = models.OneToOneField(
        PmCita,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='disponibilidad',
        verbose_name='Cita que ocupa el bloque',
    )

    # Borrado lógico, igual que el resto del proyecto: el profesional puede
    # retirar un bloque que aún nadie reservó sin perder el registro.
    estado = models.BooleanField(default=True, verbose_name='Vigente')

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    objects = PmDisponibilidad_Queryset.as_manager()

    class Meta:
        db_table = 'PmDisponibilidad'
        managed = True
        verbose_name = 'Bloque de disponibilidad'
        verbose_name_plural = 'Bloques de disponibilidad'
        ordering = ['fecha_hora']
        # Un profesional no puede publicar dos bloques que empiecen a la misma
        # hora. El solape parcial se valida en el queryset, porque depende de
        # la duración y no se puede expresar como restricción de columnas.
        constraints = [
            models.UniqueConstraint(
                fields=['profesional', 'fecha_hora'],
                name='disponibilidad_unica_por_profesional_y_hora',
            )
        ]

    def __str__(self):
        estado = 'reservado' if self.cita_id else 'libre'
        return f'{self.profesional} · {self.fecha_hora:%d/%m/%Y %H:%M} ({estado})'

    @property
    def esta_reservado(self):
        return self.cita_id is not None

    @property
    def ya_paso(self):
        return self.fecha_hora < timezone.now()

    @property
    def fecha_hora_fin(self):
        return self.fecha_hora + timedelta(minutes=self.duracion_minutos)

    @property
    def esta_disponible(self):
        """
        True si el bloque se puede reservar ahora mismo: vigente, sin cita y
        con la anticipación mínima todavía por delante. Es la misma condición
        que aplica PmDisponibilidad_Queryset.disponibles(), expuesta por
        instancia para que el serializer la entregue al frontend.
        """
        margen = timezone.now() + timedelta(hours=HORAS_MINIMAS_ANTICIPACION)
        return self.estado and not self.esta_reservado and self.fecha_hora >= margen
