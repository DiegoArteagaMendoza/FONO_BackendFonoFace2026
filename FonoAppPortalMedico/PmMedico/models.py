from django.db import models
from django.contrib.auth.hashers import make_password, check_password

from PmMedico.queryset import (
    PM_ProfesionalQueryset,
    PM_AcreditacionQueryset,
    PM_DocumentoRespaldoQueryset,
    PM_EspecialidadQueryset,
    PM_ProfesionalEspecialidadQueryset,
)
from Security.validators import validar_rut_chileno, validar_telefono, validar_archivo_documento
# Importación necesaria para Cloudinary
from cloudinary.models import CloudinaryField


# =========================================================
# REFLEJO (NO GESTIONADO) DEL ADMINISTRADOR DE FonoApp
# =========================================================
class Administrador(models.Model):
    """
    Espejo de solo lectura de la tabla FonoApp_Administracion del proyecto
    principal (FonoApp). Ambos proyectos comparten la misma base de datos
    PostgreSQL (ver docker-compose.yml en la raíz del repo), por lo que este
    modelo permite a PmMedico identificar y validar al administrador que
    aprueba/rechaza acreditaciones sin duplicar ni migrar esa tabla desde aquí
    (managed=False: Django nunca la crea, altera ni borra).
    """
    id_usuario = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    rut = models.CharField(max_length=12)
    email = models.EmailField()
    estado = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)

    class Meta:
        db_table = 'FonoApp_Administracion'
        managed = False
        verbose_name = 'Administrador (FonoApp)'
        verbose_name_plural = 'Administradores (FonoApp)'

    def __str__(self):
        return f'{self.nombre} ({self.email})'

    @property
    def es_rol_maximo(self):
        """
        El 'rol máximo' de FonoApp es SuperAdmin (is_superuser): además de todo
        lo que puede un Admin (is_staff), es el único que administra otras
        cuentas (Gestión de Usuarios, expuesta en el proyecto FonoApp). No se
        usa para gatear acciones del Portal Médico: aquí, Admin y SuperAdmin
        tienen los mismos permisos (ver Security.permissions.EsAdministrador).
        """
        return bool(self.is_superuser and self.is_active and self.estado)


# =========================================================
# MODELO 1: PM_PROFESIONAL
# =========================================================
class PM_Profesional(models.Model):
    id_profesional = models.AutoField('Código profesional', primary_key=True)

    nombres_profesional = models.CharField(max_length=100)
    apellidos_profesional = models.CharField(max_length=100)
    rut_profesional = models.CharField(max_length=12, unique=True, validators=[validar_rut_chileno])

    # Obligatorio para prestar servicio, pero opcional al momento del registro
    # (se exige recién al aprobar la acreditación, ver PM_AcreditacionQueryset.resolver).
    numero_registro_salud_profesional = models.CharField(max_length=30, blank=True, default='')

    email_profesional = models.EmailField(unique=True)
    telefono_profesional = models.CharField(max_length=20, validators=[validar_telefono])

    # Hash de la contraseña (nunca se guarda en texto plano); se maneja con
    # set_password()/check_password(), igual que django.contrib.auth.
    password_profesional = models.CharField(max_length=128)

    # Baja lógica / cuenta activa. No se borra al profesional físicamente.
    estado_cuenta_profesional = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de registro')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    especialidades = models.ManyToManyField(
        'PM_Especialidad',
        through='PM_Profesional_especialidad',
        related_name='profesionales',
        blank=True,
    )

    objects = PM_ProfesionalQueryset.as_manager()

    class Meta:
        db_table = 'PM_Profesional'
        verbose_name = 'Profesional'
        verbose_name_plural = 'Profesionales'
        ordering = ['apellidos_profesional', 'nombres_profesional']

    def __str__(self):
        return f'{self.nombres_profesional} {self.apellidos_profesional} ({self.rut_profesional})'

    def set_password(self, password_plano):
        self.password_profesional = make_password(password_plano)

    def check_password(self, password_plano):
        return check_password(password_plano, self.password_profesional)


# =========================================================
# MODELO 2: PM_ACREDITACION
# =========================================================
class PM_Acreditacion(models.Model):
    ESTADOS_VERIFICACION = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_REVISION', 'En revisión'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
    ]

    id_acreditacion = models.AutoField('Código acreditación', primary_key=True)

    id_profesional = models.ForeignKey(
        PM_Profesional,
        on_delete=models.CASCADE,
        db_column='id_profesional',
        related_name='acreditaciones',
    )

    estado_verificacion_profesional = models.CharField(
        max_length=15, choices=ESTADOS_VERIFICACION, default='PENDIENTE'
    )
    fecha_solicitud_profesional = models.DateField(verbose_name='Fecha de solicitud')
    fecha_resolucion_profesional = models.DateField(null=True, blank=True, verbose_name='Fecha de resolución')

    # Auditoría: qué administrador (de FonoApp, rol máximo) resolvió la solicitud.
    # db_constraint=False porque la tabla referenciada (FonoApp_Administracion) no
    # es gestionada por las migraciones de este proyecto.
    id_administrador_resolutor = models.ForeignKey(
        Administrador,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_administrador_resolutor',
        db_constraint=False,
        related_name='acreditaciones_resueltas',
    )

    objects = PM_AcreditacionQueryset.as_manager()

    class Meta:
        db_table = 'PM_Acreditacion'
        verbose_name = 'Acreditación'
        verbose_name_plural = 'Acreditaciones'
        ordering = ['-fecha_solicitud_profesional']

    def __str__(self):
        return f'Acreditación #{self.id_acreditacion} - {self.id_profesional} ({self.estado_verificacion_profesional})'


# =========================================================
# MODELO 3: PM_DOCUMENTO_RESPALDO
# =========================================================
class PM_Documento_Respaldo(models.Model):
    TIPOS_DOCUMENTO = [
        ('CEDULA_IDENTIDAD', 'Cédula de identidad'),
        ('CERTIFICADO_TITULO', 'Certificado de título'),
        ('CERTIFICADO_SUPERINTENDENCIA', 'Certificado Superintendencia de Salud'),
    ]

    id_documento = models.AutoField('Código documento', primary_key=True)

    id_profesional = models.ForeignKey(
        PM_Profesional,
        on_delete=models.CASCADE,
        db_column='id_profesional',
        related_name='documentos',
    )

    tipo_documeto_profesional = models.CharField(max_length=30, choices=TIPOS_DOCUMENTO)

    # ACTUALIZACIÓN A CLOUDINARY
    # CloudinaryField acepta el parámetro resource_type='raw' para manejar PDFs
    # o cualquier otro tipo de archivo no-imagen.
    url_documento_profesional = CloudinaryField(
        'documento',
        folder='pm_medico/documentos/',
        resource_type='raw'
    )

    fecha_subida_documento_profesional = models.DateTimeField(auto_now_add=True)
    documento_profesional_valido = models.BooleanField(default=False)

    objects = PM_DocumentoRespaldoQueryset.as_manager()

    class Meta:
        db_table = 'PM_Documento_Respaldo'
        verbose_name = 'Documento de respaldo'
        verbose_name_plural = 'Documentos de respaldo'
        ordering = ['-fecha_subida_documento_profesional']

    def __str__(self):
        return f'{self.get_tipo_documeto_profesional_display()} - {self.id_profesional}'


# =========================================================
# MODELO 4: PM_ESPECIALIDAD
# =========================================================
class PM_Especialidad(models.Model):
    id_especialidad = models.AutoField('Código especialidad', primary_key=True)
    nombre_especialidad_profesional = models.CharField(max_length=100, unique=True)
    especialidad_requiere_certificado = models.BooleanField(default=False)

    objects = PM_EspecialidadQueryset.as_manager()

    class Meta:
        db_table = 'PM_Especialidad'
        verbose_name = 'Especialidad'
        verbose_name_plural = 'Especialidades'
        ordering = ['nombre_especialidad_profesional']

    def __str__(self):
        return self.nombre_especialidad_profesional


# =========================================================
# MODELO 5: PM_PROFESIONAL_ESPECIALIDAD (tabla intermedia N:M)
# =========================================================
class PM_Profesional_especialidad(models.Model):
    id_profesional = models.ForeignKey(
        PM_Profesional,
        on_delete=models.CASCADE,
        db_column='id_profesional',
        related_name='profesional_especialidades',
    )
    id_especialidad = models.ForeignKey(
        PM_Especialidad,
        on_delete=models.CASCADE,
        db_column='id_especialidad',
        related_name='especialidad_profesionales',
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

    objects = PM_ProfesionalEspecialidadQueryset.as_manager()

    class Meta:
        db_table = 'PM_Profesional_especialidad'
        verbose_name = 'Especialidad del profesional'
        verbose_name_plural = 'Especialidades del profesional'
        unique_together = ('id_profesional', 'id_especialidad')

    def __str__(self):
        return f'{self.id_profesional} - {self.id_especialidad}'