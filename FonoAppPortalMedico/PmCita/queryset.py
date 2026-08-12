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
        return cita, None

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
    # Atención
    # ----------------------------------------------------------------

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
