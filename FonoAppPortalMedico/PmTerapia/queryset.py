from django.db import models, transaction
from django.utils import timezone


class PmEjercicio_Queryset(models.QuerySet):
    """
    Catálogo de ejercicios de un fonoaudiólogo.

    Todo pasa por 'de_profesional': los ejercicios son privados, y ninguna
    vista debería poder llegar a uno ajeno ni por accidente.
    """

    # ----------------------------------------------------------------
    # Consultas
    # ----------------------------------------------------------------

    def vigentes(self):
        """Los que siguen en el catálogo (no borrados)."""
        return self.filter(estado=True)

    def de_profesional(self, id_profesional):
        """Catálogo vigente de un fonoaudiólogo, del más nuevo al más antiguo."""
        return self.vigentes().filter(profesional_id=id_profesional).order_by('-fecha_creacion')

    def propio(self, id_ejercicio, id_profesional):
        """
        Un ejercicio vigente, solo si es de ese fonoaudiólogo. Devuelve None en
        cualquier otro caso: la vista responde 404 sin distinguir "no existe" de
        "no es tuyo", para no confirmar que existe.
        """
        return self.de_profesional(id_profesional).filter(id_ejercicio=id_ejercicio).first()

    # ----------------------------------------------------------------
    # Cambios
    # ----------------------------------------------------------------

    def eliminar(self, ejercicio):
        """
        Saca el ejercicio del catálogo.

        Es un borrado lógico: el registro queda por trazabilidad y porque los
        planes de terapia que lo tengan asignado deben seguir mostrándolo al
        paciente, con su video de ejemplo. El archivo solo se borra de
        Cloudinary si ningún plan lo referencia; mientras alguno lo use, se
        conserva.
        """
        ejercicio.estado = False
        ejercicio.save(update_fields=['estado', 'fecha_actualizacion'])

        if not ejercicio.esta_en_uso():
            ejercicio.eliminar_archivo_fisico()

        return ejercicio


class PmPlanTerapia_Queryset(models.QuerySet):
    """
    Planes de terapia. Las reglas de negocio están aquí y no en las vistas,
    igual que en PmCita: la vista solo traduce el resultado a una respuesta.

    Los métodos que cambian datos devuelven (plan, error): si 'error' trae un
    texto, la vista responde 400 con él.
    """

    # ----------------------------------------------------------------
    # Consultas
    # ----------------------------------------------------------------

    def activos(self):
        return self.filter(estado=self.model.Estado.ACTIVO)

    def de_profesional(self, id_profesional):
        return self.filter(profesional_id=id_profesional).select_related('cliente')

    def de_cliente(self, id_cliente):
        return self.filter(cliente_id=id_cliente).select_related('profesional')

    def propio_de_profesional(self, id_plan, id_profesional):
        """El plan solo si es de ese fonoaudiólogo; None si no (la vista responde 404)."""
        return self.de_profesional(id_profesional).filter(id_plan=id_plan).first()

    def propio_de_cliente(self, id_plan, id_cliente):
        return self.de_cliente(id_cliente).filter(id_plan=id_plan).first()

    def activo_del_par(self, id_cliente, id_profesional):
        return self.activos().filter(cliente_id=id_cliente, profesional_id=id_profesional).first()

    # ----------------------------------------------------------------
    # Crear
    # ----------------------------------------------------------------

    def crear(self, profesional, cita, ejercicios, periodicidad, indicaciones=''):
        """
        Crea el plan desde una cita realizada.

        'ejercicios' es una lista de dicts {ejercicio, indicaciones} ya
        resueltos a instancias por el serializer. Las comprobaciones que
        dependen de la base (cita realizada y del par, paciente con cuenta,
        plan activo previo) van aquí; las de forma (1 a 3 ejercicios, que sean
        del profesional) las hace el serializer antes.
        """
        from PmCita.models import PmCita
        from PmTerapia.periodos import hoy_en_chile

        if cita.profesional_id != profesional.pk:
            return None, 'Esa cita no es tuya.'

        if cita.estado != PmCita.Estado.REALIZADA:
            return None, 'Solo se puede asignar un plan después de una cita realizada.'

        # Sin cuenta no hay sesión con la que entrar a ver el plan. Al invitado
        # se le invita a crear cuenta con su mismo RUT; el frontend lo explica.
        if not cita.cliente.password_cliente:
            return None, (
                'Este paciente reservó sin cuenta. Para seguir su terapia necesita '
                'registrarse con el mismo RUT; después podrás asignarle el plan.'
            )

        if self.activo_del_par(cita.cliente_id, profesional.pk):
            return None, 'Este paciente ya tiene un plan activo contigo. Ajústalo en vez de crear otro.'

        with transaction.atomic():
            plan = self.create(
                cliente=cita.cliente,
                profesional=profesional,
                cita_origen=cita,
                periodicidad=periodicidad,
                fecha_inicio=hoy_en_chile(),
                indicaciones=indicaciones or '',
            )
            self._asignar(plan, ejercicios)

        return plan, None

    # ----------------------------------------------------------------
    # Ajustar y cerrar
    # ----------------------------------------------------------------

    def ajustar(self, plan, ejercicios=None, periodicidad=None, indicaciones=None):
        """
        Cambia ejercicios, periodicidad o indicaciones de un plan activo.

        Cambiar la periodicidad REINICIA fecha_inicio a hoy y el contador de
        recordatorios: mezclar periodos de 7 y de 15 días en la misma cuenta no
        tiene sentido. Los videos anteriores conservan su numero_periodo; el
        detalle los muestra por fecha, así que no se pierden.
        """
        from PmTerapia.periodos import hoy_en_chile

        if not plan.esta_activo:
            return None, 'Este plan está cerrado. Crea uno nuevo desde la próxima cita realizada.'

        with transaction.atomic():
            campos = []

            if periodicidad and periodicidad != plan.periodicidad:
                plan.periodicidad = periodicidad
                plan.fecha_inicio = hoy_en_chile()
                plan.ultimo_periodo_recordado = -1
                campos += ['periodicidad', 'fecha_inicio', 'ultimo_periodo_recordado']

            if indicaciones is not None:
                plan.indicaciones = indicaciones
                campos.append('indicaciones')

            if campos:
                plan.save(update_fields=campos + ['fecha_actualizacion'])

            if ejercicios is not None:
                self._asignar(plan, ejercicios)

        return plan, None

    def cerrar(self, plan):
        if not plan.esta_activo:
            return None, 'Este plan ya estaba cerrado.'

        plan.estado = self.model.Estado.CERRADO
        plan.fecha_cierre = timezone.now()
        plan.save(update_fields=['estado', 'fecha_cierre', 'fecha_actualizacion'])
        return plan, None

    # ----------------------------------------------------------------
    # Interno
    # ----------------------------------------------------------------

    def _asignar(self, plan, ejercicios):
        """
        Deja el plan exactamente con 'ejercicios' (lista de {ejercicio,
        indicaciones}), en ese orden. Los que ya estaban se actualizan o
        reactivan; los que no vienen se desactivan, nunca se borran.
        """
        from PmTerapia.models import PmPlanEjercicio

        ids_nuevos = []
        for orden, item in enumerate(ejercicios, start=1):
            asignacion, _ = PmPlanEjercicio.objects.update_or_create(
                plan=plan,
                ejercicio=item['ejercicio'],
                defaults={
                    'orden': orden,
                    'indicaciones': item.get('indicaciones') or '',
                    'estado': True,
                },
            )
            ids_nuevos.append(asignacion.pk)

        plan.asignaciones.exclude(pk__in=ids_nuevos).filter(estado=True).update(
            estado=False, fecha_actualizacion=timezone.now()
        )
