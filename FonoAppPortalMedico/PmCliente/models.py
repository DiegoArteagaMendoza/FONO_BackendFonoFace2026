from django.contrib.auth.hashers import make_password, check_password
from django.db import models

from PmCliente.queryset import PmCliente_Queryset
from Security.validators import validar_rut_chileno, validar_telefono


class PmCliente(models.Model):
    """
    Persona que se registra en el Portal Médico para optar a atenciones
    telemáticas con fonoaudiólogos.

    Tiene sesión propia (contraseña + JWT con el claim 'id_cliente'), separada
    de la del profesional y de la del administrador de FonoApp: son tres
    identidades distintas que pueden convivir en el mismo navegador.
    """
    id_cliente = models.AutoField("Codigo registro cliente", primary_key=True)

    # Datos personales
    nombres_cliente = models.CharField(max_length=100, verbose_name='Nombres')
    apellidos_clientes = models.CharField(max_length=100, verbose_name='Apellidos')
    rut_cliente = models.CharField(
        max_length=12, unique=True, verbose_name='RUT', validators=[validar_rut_chileno]
    )
    fecha_nacimiento_cliente = models.DateField(verbose_name='Fecha de nacimiento')

    # Datos de contacto
    email_cliente = models.EmailField(max_length=254, unique=True, verbose_name='Correo electrónico')
    telefono_cliente = models.CharField(
        max_length=20, verbose_name='Teléfono', validators=[validar_telefono]
    )

    # Hash de la contraseña (nunca se guarda en texto plano); se maneja con
    # set_password()/check_password(), igual que PM_Profesional.
    password_cliente = models.CharField(max_length=128, default='', verbose_name='Contraseña')

    # Metadatos de control (mismo criterio que el resto de los modelos del proyecto)
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de registro')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última actualización')
    estado = models.BooleanField(default=True, verbose_name='Activo')  # Para borrado lógico

    objects = PmCliente_Queryset.as_manager()

    class Meta:
        db_table = 'PmCliente'
        managed = True
        verbose_name = 'Cliente del Portal Médico'
        verbose_name_plural = 'Clientes del Portal Médico'
        ordering = ['-fecha_creacion']

    def set_password(self, password_plano):
        self.password_cliente = make_password(password_plano)

    def check_password(self, password_plano):
        # Un cliente registrado antes de que existieran las contraseñas tiene el
        # hash vacío: check_password devuelve False y no podrá iniciar sesión
        # hasta que se le asigne una.
        if not self.password_cliente:
            return False
        return check_password(password_plano, self.password_cliente)

    def __str__(self):
        return f'{self.nombres_cliente} {self.apellidos_clientes} ({self.rut_cliente})'
