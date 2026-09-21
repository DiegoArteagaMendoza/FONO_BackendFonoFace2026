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
    # Recordatorios
    # ----------------------------------------------------------------

    def recordatorios_pendientes(self, ahora=None):
        """
        Los planes a los que hoy corresponde mandar un recordatorio.

        Devuelve [(plan, numero_periodo, faltan)]: un plan entra cuando su
        último periodo cerrado no está cumplido y todavía no se le recordó
        (numero > ultimo_periodo_recordado). Solo se mira el último cerrado:
        reclamar periodos más viejos no ayuda al paciente, y así un cron que
        estuvo caído unos días no dispara una ráfaga de correos al volver.
        """
        from PmTerapia.periodos import ultimo_periodo_cerrado

        pendientes = []
        for plan in self.activos().select_related('cliente', 'profesional').order_by('id_plan'):
            numero = ultimo_periodo_cerrado(plan.fecha_inicio, plan.periodicidad, ahora)
            if numero is None or numero <= plan.ultimo_periodo_recordado:
                continue
            faltan = faltan_en_periodo(plan, numero)
            if faltan:
                pendientes.append((plan, numero, faltan))
        return pendientes

    def marcar_recordado(self, plan, numero):
        """Deja constancia de que ese periodo ya se recordó: nunca dos correos por el mismo."""
        plan.ultimo_periodo_recordado = numero
        plan.save(update_fields=['ultimo_periodo_recordado', 'fecha_actualizacion'])

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


class PmVideoProgreso_Queryset(models.QuerySet):
    """
    Videos del paciente practicando sus ejercicios. Misma disciplina que
    PmVideo: nunca se entrega un vencido, y eliminar es lógico (queda el
    registro con su retroalimentación; se va solo el archivo).
    """

    # ----------------------------------------------------------------
    # Consultas
    # ----------------------------------------------------------------

    def vigentes(self):
        return self.filter(estado=True, fecha_expiracion__gt=timezone.now())

    def vencidos(self):
        """Los que cumplieron sus 7 días y siguen sin eliminarse. Los lee la limpieza."""
        return self.filter(estado=True, fecha_expiracion__lte=timezone.now())

    def de_plan(self, id_plan):
        """
        Todo el historial del plan, vigentes o no: la retroalimentación de un
        video vencido sigue valiendo para el paciente. Del más nuevo al más viejo.
        """
        return (self.filter(plan_ejercicio__plan_id=id_plan)
                    .select_related('plan_ejercicio__ejercicio')
                    .order_by('-fecha_subida'))

    def que_cuentan(self):
        """
        Los videos que valen como reporte: los vigentes y los que vencieron.

        Un video que se envió y caducó a los 7 días cumplió igual; el
        vencimiento borra el archivo, no el hecho de haberlo mandado. Lo que
        no cuenta es lo que el paciente retiró (RP) o el fonoaudiólogo eliminó
        por orden médica (OM): en ambos casos alguien decidió que no valía.
        """
        return self.filter(
            models.Q(estado=True)
            | models.Q(motivo_eliminacion=self.model.MotivoEliminacion.VENCIMIENTO)
        )

    def del_periodo(self, id_plan, numero_periodo):
        """Los que cuentan como reporte en un periodo concreto (ver que_cuentan)."""
        return self.que_cuentan().filter(plan_ejercicio__plan_id=id_plan, numero_periodo=numero_periodo)

    def propio_de_cliente(self, id_video, id_cliente):
        return self.vigentes().filter(id_video=id_video, plan_ejercicio__plan__cliente_id=id_cliente).first()

    # ----------------------------------------------------------------
    # Cambios
    # ----------------------------------------------------------------

    def preparar_subida(self, plan, id_plan_ejercicio):
        """
        Resuelve a qué asignación va el video y en qué periodo cae hoy.

        Devuelve (plan_ejercicio, numero_periodo, error). Las reglas que
        dependen de la base viven aquí: el plan debe estar activo y el ejercicio
        debe seguir formando parte de él. El archivo lo valida el serializer.
        """
        from PmTerapia.periodos import periodo_actual

        if not plan.esta_activo:
            return None, None, 'Este plan está cerrado: ya no recibe videos.'

        asignacion = plan.asignaciones.filter(pk=id_plan_ejercicio, estado=True).first()
        if not asignacion:
            return None, None, 'Ese ejercicio ya no forma parte de tu plan.'

        return asignacion, periodo_actual(plan.fecha_inicio, plan.periodicidad), None

    def eliminar(self, video, motivo):
        """
        Borra el archivo de Cloudinary y marca el registro con el motivo. El
        registro se conserva: la fecha y la retroalimentación siguen siendo
        parte del historial del paciente.
        """
        if not video.estado:
            return False

        video.eliminar_archivo_fisico()
        video.estado = False
        video.motivo_eliminacion = motivo
        video.fecha_eliminacion = timezone.now()
        video.save(update_fields=['estado', 'motivo_eliminacion', 'fecha_eliminacion', 'video'])
        return True


# ======================================================================
# Cumplimiento
# ----------------------------------------------------------------------
# Lo consulta el seguimiento del fonoaudiólogo (semáforo y detalle) y el
# recordatorio diario. Vive aquí porque cruza periodos (puros, periodos.py)
# con los videos que hay en la base.
# ======================================================================

def faltan_en_periodo(plan, numero):
    """
    Nombres de los ejercicios activos del plan sin video que cuente en ese
    periodo. Lista vacía = periodo cumplido. Es lo que lee el recordatorio,
    que solo mira un periodo y no necesita el detalle completo.
    """
    from PmTerapia.models import PmVideoProgreso

    con_video = set(
        PmVideoProgreso.objects.del_periodo(plan.pk, numero)
        .values_list('plan_ejercicio_id', flat=True)
    )
    return [pe.ejercicio.nombre for pe in plan.ejercicios_activos() if pe.pk not in con_video]


def cumplimiento_de(plan, ahora=None):
    """
    Estado del plan frente a sus periodos ya cerrados.

    Devuelve un dict:
      al_dia            True si todos los periodos cerrados están cumplidos.
      periodos_cerrados [{numero, desde, hasta, cumplido, faltan: [nombres]}]
                        del más reciente al más antiguo.
      ultimo_video      fecha del último video que cuenta, o None.

    Un periodo está cumplido cuando cada ejercicio activo del plan tiene al
    menos un video que cuente como reporte (ver PmVideoProgreso_Queryset.
    que_cuentan) con ese numero_periodo. El periodo en curso nunca se evalúa:
    todavía puede cumplirse.
    """
    from PmTerapia.models import PmVideoProgreso
    from PmTerapia.periodos import periodos_cerrados, rango_de_periodo

    ejercicios = list(plan.ejercicios_activos())
    ids_ejercicios = [pe.pk for pe in ejercicios]

    # Una sola consulta: (periodo, plan_ejercicio) de todo lo que cuenta.
    pares = set(
        PmVideoProgreso.objects.que_cuentan()
        .filter(plan_ejercicio__in=ids_ejercicios)
        .values_list('numero_periodo', 'plan_ejercicio_id')
    )

    detalle = []
    for numero in reversed(periodos_cerrados(plan.fecha_inicio, plan.periodicidad, ahora)):
        faltan = [pe.ejercicio.nombre for pe in ejercicios if (numero, pe.pk) not in pares]
        desde, hasta = rango_de_periodo(plan.fecha_inicio, plan.periodicidad, numero)
        detalle.append({
            'numero': numero,
            'desde': desde.isoformat(),
            'hasta': hasta.isoformat(),
            'cumplido': not faltan,
            'faltan': faltan,
        })

    ultimo = (
        PmVideoProgreso.objects.que_cuentan()
        .filter(plan_ejercicio__plan=plan)
        .order_by('-fecha_subida')
        .values_list('fecha_subida', flat=True)
        .first()
    )

    return {
        'al_dia': all(p['cumplido'] for p in detalle),
        'periodos_cerrados': detalle,
        'ultimo_video': ultimo,
    }
