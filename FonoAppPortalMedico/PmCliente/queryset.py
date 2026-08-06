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

    def eliminar_logico(self, id_cliente):
        """Realiza la baja lógica del cliente cambiando su estado a False."""
        return self.filter(id_cliente=id_cliente, estado=True).update(estado=False)

    def editar_cliente(self, id_cliente, **datos):
        """Actualiza los campos indicados de un cliente activo."""
        return self.filter(id_cliente=id_cliente, estado=True).update(**datos)
