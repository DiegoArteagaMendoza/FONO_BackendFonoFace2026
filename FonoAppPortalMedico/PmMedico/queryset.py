from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone


# =========================================================
# PM_PROFESIONAL
# =========================================================
class PM_ProfesionalQueryset(models.QuerySet):

    def activos(self):
        """Solo profesionales con la cuenta activa (no eliminados lógicamente)."""
        return self.filter(estado_cuenta_profesional=True)

    def con_detalles(self):
        """Evita el problema N+1 al traer acreditaciones, documentos y especialidades."""
        return self.prefetch_related('acreditaciones', 'documentos', 'especialidades')

    def verificados(self):
        """
        Profesionales activos cuya acreditación vigente (la más reciente) está APROBADA.
        Es la base del directorio público de fonoaudiólogos habilitados para atender.
        """
        return self.activos().filter(
            acreditaciones__estado_verificacion_profesional='APROBADO'
        ).distinct()

    @transaction.atomic
    def crear_profesional(self, nombres, apellidos, rut, email, telefono, password, numero_registro_salud=None):
        """
        Registra un nuevo profesional y abre automáticamente su solicitud de
        acreditación en estado PENDIENTE. Se mantiene deliberadamente simple/ágil:
        no exige documentos ni número de registro de salud en este paso.
        """
        from .models import PM_Acreditacion

        profesional = self.model(
            nombres_profesional=nombres,
            apellidos_profesional=apellidos,
            rut_profesional=rut,
            email_profesional=email,
            telefono_profesional=telefono,
            numero_registro_salud_profesional=numero_registro_salud or '',
        )
        # Valida la fortaleza de la contraseña en texto plano (AUTH_PASSWORD_VALIDATORS)
        # ANTES de hashearla; una vez hasheada ya no tiene sentido validarla como texto.
        # Se asocia al campo 'password' explícitamente para que el error llegue
        # anidado igual que el resto (ej: {"password": ["..."]}) y no como una
        # lista suelta sin campo asociado.
        try:
            validate_password(password, user=profesional)
        except ValidationError as error:
            raise ValidationError({'password': error.messages})
        profesional.set_password(password)
        profesional.full_clean(exclude=['password_profesional'])
        profesional.save()

        PM_Acreditacion.objects.create(
            id_profesional=profesional,
            estado_verificacion_profesional='PENDIENTE',
            fecha_solicitud_profesional=timezone.localdate(),
        )

        return profesional

    def autenticar(self, identificador, password):
        """
        Busca al profesional por email o RUT (indistintamente) y valida su contraseña.
        Retorna None si no existe, si está inactivo o si la contraseña no coincide,
        sin distinguir el motivo para no filtrar información a un atacante.
        """
        profesional = self.filter(
            models.Q(email_profesional__iexact=identificador) | models.Q(rut_profesional=identificador)
        ).first()

        if not profesional or not profesional.estado_cuenta_profesional:
            return None

        return profesional if profesional.check_password(password) else None

    def editar_datos(self, id_profesional, **datos_a_actualizar):
        """
        Actualiza únicamente datos de contacto/perfil. Los campos sensibles
        (contraseña, estado de cuenta, verificación) tienen sus propios métodos
        para no quedar expuestos a una actualización masiva accidental.
        """
        campos_prohibidos = (
            'id_profesional', 'password_profesional', 'estado_cuenta_profesional',
        )
        for campo in campos_prohibidos:
            datos_a_actualizar.pop(campo, None)

        if not datos_a_actualizar:
            return False

        filas_actualizadas = self.filter(
            id_profesional=id_profesional, estado_cuenta_profesional=True
        ).update(**datos_a_actualizar)

        return filas_actualizadas > 0

    def cambiar_password(self, id_profesional, password_actual, password_nueva):
        """Cambia la contraseña solo si la actual es correcta (evita robo de sesión)."""
        try:
            profesional = self.get(id_profesional=id_profesional, estado_cuenta_profesional=True)
        except self.model.DoesNotExist:
            return False, 'Profesional no encontrado o inactivo.'

        if not profesional.check_password(password_actual):
            return False, 'La contraseña actual no es correcta.'

        try:
            validate_password(password_nueva, user=profesional)
        except ValidationError as error:
            return False, ' '.join(error.messages)

        profesional.set_password(password_nueva)
        profesional.save(update_fields=['password_profesional'])
        return True, 'Contraseña actualizada correctamente.'

    def eliminar_logico(self, id_profesional):
        """Baja lógica: el profesional deja de poder autenticarse ni prestar servicios."""
        filas_actualizadas = self.filter(id_profesional=id_profesional).update(estado_cuenta_profesional=False)
        return filas_actualizadas > 0


# =========================================================
# PM_ACREDITACION
# =========================================================
class PM_AcreditacionQueryset(models.QuerySet):

    def de_profesional(self, id_profesional):
        return self.filter(id_profesional_id=id_profesional).order_by('-fecha_solicitud_profesional')

    def vigente_de(self, id_profesional):
        """La solicitud de acreditación más reciente de un profesional."""
        return self.de_profesional(id_profesional).first()

    def pendientes(self):
        """Cola de trabajo para el administrador: lo que aún falta auditar."""
        return self.filter(
            estado_verificacion_profesional__in=['PENDIENTE', 'EN_REVISION']
        ).select_related('id_profesional').order_by('fecha_solicitud_profesional')

    def marcar_en_revision(self, id_acreditacion):
        """Se invoca al recibir el primer documento: saca la solicitud de la cola de 'nuevas'."""
        return self.filter(
            id_acreditacion=id_acreditacion, estado_verificacion_profesional='PENDIENTE'
        ).update(estado_verificacion_profesional='EN_REVISION')

    def resolver(self, id_acreditacion, administrador, nuevo_estado):
        """
        Aplica la resolución (APROBADO/RECHAZADO) de un administrador (Admin o
        SuperAdmin). Antes de aprobar, exige que el profesional cumpla los
        requisitos mínimos: número de registro de salud informado y al menos
        un documento validado.
        """
        if nuevo_estado not in ('APROBADO', 'RECHAZADO'):
            raise ValueError("El estado de resolución debe ser 'APROBADO' o 'RECHAZADO'.")

        try:
            acreditacion = self.select_related('id_profesional').get(pk=id_acreditacion)
        except self.model.DoesNotExist:
            return None, 'Solicitud de acreditación no encontrada.'

        if acreditacion.estado_verificacion_profesional in ('APROBADO', 'RECHAZADO'):
            return None, 'Esta solicitud ya fue resuelta anteriormente.'

        profesional = acreditacion.id_profesional

        if nuevo_estado == 'APROBADO':
            if not profesional.numero_registro_salud_profesional:
                return None, 'El profesional no ha informado su número de registro de salud.'
            if not profesional.documentos.filter(documento_profesional_valido=True).exists():
                return None, 'El profesional no cuenta con al menos un documento validado.'
            # Elegir especialidades es el paso 3 del proceso que se le muestra al
            # profesional (ver pasos-acreditacion en el frontend), pero no se
            # estaba exigiendo aquí. Sin especialidades, el profesional queda
            # aprobado y reservable, pero invisible para cualquier paciente que
            # filtre por especialidad al buscar hora.
            if not profesional.especialidades.exists():
                return None, 'El profesional no ha declarado ninguna especialidad.'

        acreditacion.estado_verificacion_profesional = nuevo_estado
        acreditacion.fecha_resolucion_profesional = timezone.localdate()
        acreditacion.id_administrador_resolutor_id = administrador.pk
        acreditacion.save(update_fields=[
            'estado_verificacion_profesional', 'fecha_resolucion_profesional', 'id_administrador_resolutor'
        ])

        return acreditacion, None


# =========================================================
# PM_DOCUMENTO_RESPALDO
# =========================================================
class PM_DocumentoRespaldoQueryset(models.QuerySet):

    def de_profesional(self, id_profesional):
        return self.filter(id_profesional_id=id_profesional).order_by('-fecha_subida_documento_profesional')

    @transaction.atomic
    def subir_documento(self, profesional, tipo_documento, archivo):
        """
        Registra un documento de respaldo y, si la acreditación seguía en
        PENDIENTE, la mueve automáticamente a EN_REVISION.
        """
        from .models import PM_Acreditacion

        documento = self.create(
            id_profesional=profesional,
            tipo_documeto_profesional=tipo_documento,
            url_documento_profesional=archivo,
        )

        PM_Acreditacion.objects.filter(
            id_profesional=profesional, estado_verificacion_profesional='PENDIENTE'
        ).update(estado_verificacion_profesional='EN_REVISION')

        return documento

    def marcar_validez(self, id_documento, es_valido):
        """Un administrador (Admin o SuperAdmin) marca (o desmarca) un documento como válido."""
        filas_actualizadas = self.filter(id_documento=id_documento).update(documento_profesional_valido=es_valido)
        return filas_actualizadas > 0

    def eliminar_si_no_validado(self, id_documento, id_profesional):
        """
        Permite al profesional borrar su propio documento mientras no haya sido
        validado; una vez validado, forma parte del expediente de auditoría y ya
        no puede eliminarse desde este endpoint.
        """
        try:
            documento = self.get(id_documento=id_documento, id_profesional_id=id_profesional)
        except self.model.DoesNotExist:
            return False, 'Documento no encontrado.'

        if documento.documento_profesional_valido:
            return False, 'No se puede eliminar un documento ya validado.'

        documento.url_documento_profesional.delete(save=False)
        documento.delete()
        return True, 'Documento eliminado correctamente.'


# =========================================================
# PM_ESPECIALIDAD
# =========================================================
class PM_EspecialidadQueryset(models.QuerySet):

    def buscar(self, texto):
        return self.filter(nombre_especialidad_profesional__icontains=texto)


# =========================================================
# PM_PROFESIONAL_ESPECIALIDAD
# =========================================================
class PM_ProfesionalEspecialidadQueryset(models.QuerySet):

    def de_profesional(self, id_profesional):
        return self.filter(id_profesional_id=id_profesional).select_related('id_especialidad')

    def asignar(self, profesional, especialidad):
        """
        Vincula una especialidad al profesional. Si la especialidad exige
        certificado, exige que el profesional ya tenga al menos un documento
        validado antes de poder reclamarla.
        """
        if especialidad.especialidad_requiere_certificado:
            if not profesional.documentos.filter(documento_profesional_valido=True).exists():
                raise ValidationError(
                    'Esta especialidad requiere un certificado validado antes de poder asignarla.'
                )

        relacion, creada = self.get_or_create(id_profesional=profesional, id_especialidad=especialidad)
        return relacion, creada

    def quitar(self, id_profesional, id_especialidad):
        filas_eliminadas, _ = self.filter(
            id_profesional_id=id_profesional, id_especialidad_id=id_especialidad
        ).delete()
        return filas_eliminadas > 0
