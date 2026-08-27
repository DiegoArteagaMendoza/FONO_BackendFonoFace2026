from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class PmCita_Queryset(models.QuerySet):

    # ----------------------------------------------------------------
    # Consultas
    # ----------------------------------------------------------------

    def de_cliente(self, id_cliente):
        """Historial completo (incluye canceladas y realizadas) de un cliente."""
        return self.filter(cliente_id=id_cliente)

    def de_profesional(self, id_profesional):
        """Historial completo de un profesional."""
        return self.filter(profesional_id=id_profesional)

    def activas(self):
        """Citas reservadas: aún no canceladas ni realizadas."""
        return self.filter(estado=self.model.Estado.RESERVADA)

    def proximas(self):
        """Citas activas cuya fecha/hora todavía no ocurre."""
        return self.activas().filter(fecha_hora__gte=timezone.now())

    def proximas_de_cliente(self, id_cliente):
        return self.proximas().filter(cliente_id=id_cliente)

    def proximas_de_profesional(self, id_profesional):
        return self.proximas().filter(profesional_id=id_profesional)

    # ----------------------------------------------------------------
    # Reserva
    # ----------------------------------------------------------------

    def _hay_solape(self, profesional_id, fecha_hora, duracion_minutos, excluir_id=None):
        """
        True si el profesional ya tiene otra cita activa cuyo rango horario
        [fecha_hora, fecha_hora + duración) se cruza con el que se propone.
        Evita que un mismo profesional quede doblemente agendado.
        """
        inicio = fecha_hora
        fin = fecha_hora + timedelta(minutes=duracion_minutos)

        candidatas = self.activas().filter(profesional_id=profesional_id)
        if excluir_id:
            candidatas = candidatas.exclude(pk=excluir_id)

        for cita in candidatas:
            otro_inicio = cita.fecha_hora
            otro_fin = otro_inicio + timedelta(minutes=cita.duracion_minutos)
            if inicio < otro_fin and otro_inicio < fin:
                return True
        return False

    @transaction.atomic
    def reservar(self, cliente, profesional, fecha_hora, motivo_consulta='', duracion_minutos=None):
        """
        Reserva una nueva cita. Exige que el profesional esté acreditado
        (APROBADO), que la hora tenga la anticipación mínima y que no se
        cruce con otra cita activa del mismo profesional.
        """
        from PmCita.models import DURACION_MINUTOS_DEFECTO, HORAS_MINIMAS_ANTICIPACION

        duracion_minutos = duracion_minutos or DURACION_MINUTOS_DEFECTO

        if not type(profesional).objects.verificados().filter(pk=profesional.pk).exists():
            raise ValidationError('El profesional seleccionado no está acreditado para atender.')

        margen_minimo = timezone.now() + timedelta(hours=HORAS_MINIMAS_ANTICIPACION)
        if fecha_hora < margen_minimo:
            raise ValidationError(
                f'La cita debe reservarse con al menos {HORAS_MINIMAS_ANTICIPACION} horas de anticipación.'
            )

        if self._hay_solape(profesional.pk, fecha_hora, duracion_minutos):
            raise ValidationError('El profesional ya tiene otra cita agendada en ese horario.')

        return self.create(
            cliente=cliente,
            profesional=profesional,
            fecha_hora=fecha_hora,
            duracion_minutos=duracion_minutos,
            motivo_consulta=motivo_consulta,
        )

    # ----------------------------------------------------------------
    # Cancelación (el cliente no realizará la cita / el profesional la anula)
    # ----------------------------------------------------------------

    def _cancelar(self, cita, origen, motivo):
        from PmCita.models import HORAS_MINIMAS_ANTICIPACION

        if not cita.esta_activa:
            return None, 'Solo se pueden cancelar citas que sigan reservadas.'
        if not cita.permite_cambios():
            return None, (
                f'Ya no se puede cancelar: faltan menos de {HORAS_MINIMAS_ANTICIPACION} '
                'horas para la cita.'
            )

        cita.estado = (
            self.model.Estado.CANCELADA_CLIENTE
            if origen == self.model.Origen.CLIENTE
            else self.model.Estado.CANCELADA_MEDICO
        )
        cita.motivo_cancelacion = motivo or ''
        cita.fecha_cancelacion = timezone.now()
        cita.cancelada_por = origen
        cita.save(update_fields=['estado', 'motivo_cancelacion', 'fecha_cancelacion', 'cancelada_por'])

        # Si la cita venía de un bloque publicado, ese horario del profesional
        # queda libre otra vez y vuelve a ofrecerse. Sin esto, cada cancelación
        # le comería una hora de agenda al profesional para siempre.
        self._liberar_bloque(cita)

        return cita, None

    def _liberar_bloque(self, cita):
        """Desliga el bloque de disponibilidad de una cita que dejó de estar activa."""
        from PmCita.models import PmDisponibilidad

        PmDisponibilidad.objects.filter(cita_id=cita.pk).update(cita=None)

    def cancelar_por_cliente(self, id_cita, id_cliente, motivo=None):
        """Solo el dueño de la cita puede cancelarla."""
        try:
            cita = self.get(pk=id_cita, cliente_id=id_cliente)
        except self.model.DoesNotExist:
            return None, 'Cita no encontrada.'
        return self._cancelar(cita, self.model.Origen.CLIENTE, motivo)

    def cancelar_por_profesional(self, id_cita, id_profesional, motivo=None):
        """Solo el profesional asignado puede cancelarla."""
        try:
            cita = self.get(pk=id_cita, profesional_id=id_profesional)
        except self.model.DoesNotExist:
            return None, 'Cita no encontrada.'
        return self._cancelar(cita, self.model.Origen.PROFESIONAL, motivo)

    # ----------------------------------------------------------------
    # Reprogramación (posponer a una nueva fecha/hora)
    # ----------------------------------------------------------------

    def _reprogramar(self, cita, nueva_fecha_hora, origen, motivo):
        from PmCita.models import HORAS_MINIMAS_ANTICIPACION, REPROGRAMACIONES_MAXIMAS

        if not cita.esta_activa:
            return None, 'Solo se pueden reprogramar citas que sigan reservadas.'
        if not cita.permite_cambios():
            return None, (
                f'Ya no se puede reprogramar: faltan menos de {HORAS_MINIMAS_ANTICIPACION} '
                'horas para la cita.'
            )
        if cita.veces_reprogramada >= REPROGRAMACIONES_MAXIMAS:
            return None, (
                f'Esta cita ya alcanzó el máximo de {REPROGRAMACIONES_MAXIMAS} reprogramaciones; '
                'cancélela y reserve una nueva.'
            )

        margen_minimo = timezone.now() + timedelta(hours=HORAS_MINIMAS_ANTICIPACION)
        if nueva_fecha_hora < margen_minimo:
            return None, f'La nueva fecha debe tener al menos {HORAS_MINIMAS_ANTICIPACION} horas de anticipación.'

        if self._hay_solape(cita.profesional_id, nueva_fecha_hora, cita.duracion_minutos, excluir_id=cita.pk):
            return None, 'El profesional ya tiene otra cita agendada en ese nuevo horario.'

        if not cita.fecha_hora_original:
            cita.fecha_hora_original = cita.fecha_hora

        # La cita se mueve a una hora que el profesional no publicó como bloque,
        # así que el bloque original deja de corresponder y se libera: esa hora
        # vuelve a estar disponible para quien la quiera.
        self._liberar_bloque(cita)

        cita.fecha_hora = nueva_fecha_hora
        cita.veces_reprogramada += 1
        cita.motivo_reprogramacion = motivo or ''
        cita.reprogramada_por = origen
        cita.fecha_ultima_reprogramacion = timezone.now()
        cita.save(update_fields=[
            'fecha_hora', 'fecha_hora_original', 'veces_reprogramada',
            'motivo_reprogramacion', 'reprogramada_por', 'fecha_ultima_reprogramacion',
        ])
        return cita, None

    def posponer_por_cliente(self, id_cita, id_cliente, nueva_fecha_hora, motivo=None):
        try:
            cita = self.get(pk=id_cita, cliente_id=id_cliente)
        except self.model.DoesNotExist:
            return None, 'Cita no encontrada.'
        return self._reprogramar(cita, nueva_fecha_hora, self.model.Origen.CLIENTE, motivo)

    def posponer_por_profesional(self, id_cita, id_profesional, nueva_fecha_hora, motivo=None):
        try:
            cita = self.get(pk=id_cita, profesional_id=id_profesional)
        except self.model.DoesNotExist:
            return None, 'Cita no encontrada.'
        return self._reprogramar(cita, nueva_fecha_hora, self.model.Origen.PROFESIONAL, motivo)

    # ----------------------------------------------------------------
    # Gestión por código de seguimiento (sin cuenta)
    # ----------------------------------------------------------------

    def por_codigo(self, codigo):
        """
        Busca una cita por su código de seguimiento.

        La comparación ignora mayúsculas y espacios porque el código se teclea
        desde un correo, y nadie debería fallar por copiarlo con un espacio al
        final o en minúsculas.
        """
        codigo = (codigo or '').strip().replace(' ', '').upper()
        if not codigo:
            return None
        return self.filter(codigo_seguimiento__iexact=codigo).first()

    def cancelar_por_codigo(self, codigo, motivo=None):
        """Cancela desde el seguimiento; cuenta como cancelación del cliente."""
        cita = self.por_codigo(codigo)
        if not cita:
            return None, 'Cita no encontrada.'
        return self._cancelar(cita, self.model.Origen.CLIENTE, motivo)

    def posponer_por_codigo(self, codigo, nueva_fecha_hora, motivo=None):
        """Reprograma desde el seguimiento; cuenta como cambio del cliente."""
        cita = self.por_codigo(codigo)
        if not cita:
            return None, 'Cita no encontrada.'
        return self._reprogramar(cita, nueva_fecha_hora, self.model.Origen.CLIENTE, motivo)

    # ----------------------------------------------------------------
    # Atención
    # ----------------------------------------------------------------

    def reservar_bloque(self, cliente, disponibilidad, motivo_consulta=''):
        """
        Reserva la cita a partir de un bloque publicado por el profesional.

        A diferencia de reservar(), aquí la fecha y la duración NO las propone
        el paciente: salen del bloque. Se sigue comprobando la acreditación y
        la anticipación mínima, porque un bloque pudo publicarse hace días y
        estar a punto de ocurrir.
        """
        from PmCita.models import PmDisponibilidad, HORAS_MINIMAS_ANTICIPACION

        profesional = disponibilidad.profesional

        if not type(profesional).objects.verificados().filter(pk=profesional.pk).exists():
            raise ValidationError('El profesional seleccionado no está acreditado para atender.')

        with transaction.atomic():
            # select_for_update evita que dos pacientes tomen el mismo bloque a
            # la vez: el segundo espera y encuentra la cita ya asignada.
            bloqueado = PmDisponibilidad.objects.select_for_update().get(pk=disponibilidad.pk)

            if not bloqueado.estado:
                raise ValidationError('Esa hora ya no está disponible.')
            if bloqueado.cita_id is not None:
                raise ValidationError('Esa hora acaba de ser tomada por otra persona.')

            margen_minimo = timezone.now() + timedelta(hours=HORAS_MINIMAS_ANTICIPACION)
            if bloqueado.fecha_hora < margen_minimo:
                raise ValidationError(
                    f'La cita debe reservarse con al menos {HORAS_MINIMAS_ANTICIPACION} horas de anticipación.'
                )

            cita = self.create(
                cliente=cliente,
                profesional=profesional,
                fecha_hora=bloqueado.fecha_hora,
                duracion_minutos=bloqueado.duracion_minutos,
                motivo_consulta=motivo_consulta,
            )

            bloqueado.cita = cita
            bloqueado.save(update_fields=['cita'])

        return cita

    def marcar_realizada(self, id_cita, id_profesional):
        """El profesional confirma que la atención se llevó a cabo."""
        try:
            cita = self.get(pk=id_cita, profesional_id=id_profesional)
        except self.model.DoesNotExist:
            return None, 'Cita no encontrada.'

        if not cita.esta_activa:
            return None, 'Solo se pueden marcar como realizadas las citas reservadas.'

        cita.estado = self.model.Estado.REALIZADA
        cita.fecha_marcada_realizada = timezone.now()
        cita.save(update_fields=['estado', 'fecha_marcada_realizada'])
        return cita, None


class PmDisponibilidad_Queryset(models.QuerySet):
    """
    Bloques horarios que los profesionales publican para ser reservados.

    La regla central: un bloque solo se puede tomar si está vigente, sin cita
    asignada y con la anticipación mínima todavía por delante. Esa condición
    vive en disponibles() y es la que consulta tanto el listado público como
    la reserva.
    """

    # ----------------------------------------------------------------
    # Consultas
    # ----------------------------------------------------------------

    def vigentes(self):
        """Bloques no retirados por el profesional."""
        return self.filter(estado=True)

    def de_profesional(self, id_profesional):
        """Todos los bloques de un profesional, ocupados o no."""
        return self.vigentes().filter(profesional_id=id_profesional)

    def libres(self):
        """Bloques vigentes que todavía no tienen una cita asignada."""
        return self.vigentes().filter(cita__isnull=True)

    def disponibles(self):
        """
        Bloques que un paciente puede reservar ahora mismo: libres y con al
        menos la anticipación mínima por delante. Es lo único que se expone
        públicamente.
        """
        from PmCita.models import HORAS_MINIMAS_ANTICIPACION

        margen = timezone.now() + timedelta(hours=HORAS_MINIMAS_ANTICIPACION)
        return self.libres().filter(fecha_hora__gte=margen)

    def disponibles_de_profesional(self, id_profesional):
        return self.disponibles().filter(profesional_id=id_profesional)

    def proximos_de_profesional(self, id_profesional):
        """Agenda publicada de un profesional de aquí en adelante, libre u ocupada."""
        return self.de_profesional(id_profesional).filter(fecha_hora__gte=timezone.now())

    # ----------------------------------------------------------------
    # Publicación
    # ----------------------------------------------------------------

    def _hay_solape(self, profesional_id, fecha_hora, duracion_minutos):
        """
        True si el bloque propuesto se cruza con otro ya publicado del mismo
        profesional. Mismo criterio que el solape de citas: los intervalos se
        tratan como [inicio, fin), de modo que un bloque que termina a las
        10:00 y otro que empieza a las 10:00 no se consideran cruzados.
        """
        inicio = fecha_hora
        fin = fecha_hora + timedelta(minutes=duracion_minutos)

        for bloque in self.de_profesional(profesional_id):
            otro_inicio = bloque.fecha_hora
            otro_fin = otro_inicio + timedelta(minutes=bloque.duracion_minutos)
            if inicio < otro_fin and otro_inicio < fin:
                return True
        return False

    def publicar(self, profesional, fecha_hora, duracion_minutos=None):
        """
        Publica un bloque. Exige que sea futuro, que la duración esté dentro
        del rango permitido y que no se cruce con otro bloque del profesional.
        """
        from PmCita.models import (
            DURACION_MINUTOS_DEFECTO,
            DURACION_MINUTOS_MINIMA,
            DURACION_MINUTOS_MAXIMA,
        )

        duracion_minutos = duracion_minutos or DURACION_MINUTOS_DEFECTO

        if not (DURACION_MINUTOS_MINIMA <= duracion_minutos <= DURACION_MINUTOS_MAXIMA):
            raise ValidationError(
                f'La duración debe estar entre {DURACION_MINUTOS_MINIMA} y '
                f'{DURACION_MINUTOS_MAXIMA} minutos.'
            )

        if fecha_hora < timezone.now():
            raise ValidationError('No se puede publicar una hora que ya pasó.')

        if self._hay_solape(profesional.pk, fecha_hora, duracion_minutos):
            raise ValidationError('Ya tiene otra hora publicada que se cruza con ese horario.')

        return self.create(
            profesional=profesional,
            fecha_hora=fecha_hora,
            duracion_minutos=duracion_minutos,
        )

    @transaction.atomic
    def publicar_varios(self, profesional, fechas_hora, duracion_minutos=None):
        """
        Publica varios bloques de una vez (por ejemplo, toda una mañana).

        Devuelve (creados, rechazados). Los rechazados no interrumpen al resto:
        publicar diez horas y que una se cruce con algo previo no debería
        obligar a repetir las otras nueve, así que cada una se evalúa aparte y
        el motivo del rechazo viaja de vuelta para mostrarlo.
        """
        creados = []
        rechazados = []

        for fecha_hora in fechas_hora:
            try:
                creados.append(self.publicar(profesional, fecha_hora, duracion_minutos))
            except ValidationError as error:
                rechazados.append({
                    'fecha_hora': fecha_hora,
                    'motivo': ' '.join(error.messages),
                })

        return creados, rechazados

    # ----------------------------------------------------------------
    # Retiro
    # ----------------------------------------------------------------

    def retirar(self, id_disponibilidad, id_profesional):
        """
        El profesional retira un bloque que publicó. Baja lógica, como el resto
        del proyecto.

        Un bloque ya reservado no se puede retirar: dejaría a la cita sin el
        horario que la respalda y el paciente se enteraría de que no lo atienden
        solo al llegar. Para eso está cancelar la cita, que sí avisa y registra
        el motivo.
        """
        try:
            bloque = self.get(pk=id_disponibilidad, profesional_id=id_profesional, estado=True)
        except self.model.DoesNotExist:
            return None, 'Bloque no encontrado.'

        if bloque.esta_reservado:
            return None, (
                'Esa hora ya fue reservada por un paciente. Si no puede atenderla, '
                'cancele la cita indicando el motivo.'
            )

        bloque.estado = False
        bloque.save(update_fields=['estado'])
        return bloque, None
