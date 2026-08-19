from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import models


class PmCliente_Queryset(models.QuerySet):

    def activos(self):
        """Retorna solo los clientes activos (no dados de baja)."""
        return self.filter(estado=True)

    def por_rut(self, rut):
        """Busca un cliente activo por su RUT."""
        return self.activos().filter(rut_cliente=rut)

    def buscar(self, texto):
        """Búsqueda simple por nombres, apellidos, RUT o correo."""
        return self.activos().filter(
            models.Q(nombres_cliente__icontains=texto) |
            models.Q(apellidos_clientes__icontains=texto) |
            models.Q(rut_cliente__icontains=texto) |
            models.Q(email_cliente__icontains=texto)
        )

    def crear_cliente(self, nombres, apellidos, rut, fecha_nacimiento, email, telefono, password):
        """
        Registra a un paciente con su contraseña ya hasheada.
        Mismo criterio que PM_ProfesionalQueryset.crear_profesional: la fortaleza
        de la contraseña se valida en texto plano (AUTH_PASSWORD_VALIDATORS)
        ANTES de hashearla, y el error se asocia al campo 'password' para que
        llegue anidado igual que el resto.
        """
        cliente = self.model(
            nombres_cliente=nombres,
            apellidos_clientes=apellidos,
            rut_cliente=rut,
            fecha_nacimiento_cliente=fecha_nacimiento,
            email_cliente=email,
            telefono_cliente=telefono,
        )

        try:
            validate_password(password, user=cliente)
        except ValidationError as error:
            raise ValidationError({'password': error.messages})

        cliente.set_password(password)
        cliente.full_clean(exclude=['password_cliente'])
        cliente.save()
        return cliente

    def autenticar(self, identificador, password):
        """
        Busca al paciente por correo o RUT (indistintamente) y valida su contraseña.
        Retorna None si no existe, si está inactivo o si la contraseña no coincide,
        sin distinguir el motivo para no filtrar información a un atacante.
        """
        # El RUT se compara sin distinguir mayúsculas (la K puede venir en
        # cualquier caso) y tolerando puntos, que es como suele escribirlo la gente.
        rut_normalizado = (identificador or '').replace('.', '').replace(' ', '').strip()

        cliente = self.filter(
            models.Q(email_cliente__iexact=identificador) |
            models.Q(rut_cliente__iexact=rut_normalizado)
        ).first()

        if not cliente or not cliente.estado:
            return None

        return cliente if cliente.check_password(password) else None

    def eliminar_logico(self, id_cliente):
        """Realiza la baja lógica del cliente cambiando su estado a False."""
        return self.filter(id_cliente=id_cliente, estado=True).update(estado=False)

    def editar_cliente(self, id_cliente, **datos):
        """
        Actualiza datos de contacto/perfil. Los campos sensibles (contraseña,
        RUT y estado) quedan fuera para que una actualización masiva accidental
        no los toque: cada uno tiene su propio flujo.
        """
        campos_prohibidos = ('id_cliente', 'password_cliente', 'rut_cliente', 'estado')
        datos_limpios = {k: v for k, v in datos.items() if k not in campos_prohibidos}

        if not datos_limpios:
            return 0

        return self.filter(id_cliente=id_cliente, estado=True).update(**datos_limpios)
