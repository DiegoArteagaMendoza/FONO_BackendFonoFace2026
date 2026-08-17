from rest_framework.permissions import BasePermission

from PmCliente.models import PmCliente
from PmMedico.models import Administrador, PM_Profesional


class EsAdministrador(BasePermission):
    """
    Cualquier cuenta de administrador de FonoApp con al menos el rol Admin
    (is_staff): tanto Admin como SuperAdmin lo cumplen, ya que SuperAdmin
    siempre implica is_staff=True (ver FonoAppAdministracion.queryset.
    editar_usuario_parcial). Cubre TODAS las acciones del Portal Médico
    (lecturas administrativas, validar documentos, resolver acreditaciones,
    gestionar el catálogo de especialidades): en el modelo de 3 roles del
    sistema, lo único exclusivo de SuperAdmin es la Gestión de Usuarios de
    FonoApp, que este backend ni siquiera expone.
    """
    message = 'Debe autenticarse como administrador (Admin o SuperAdmin) de FonoApp.'

    def has_permission(self, request, view):
        usuario = request.user
        return isinstance(usuario, Administrador) and usuario.is_staff


class EsProfesional(BasePermission):
    """El autenticado debe ser un profesional (no un administrador)."""
    message = 'Debe iniciar sesión como profesional para realizar esta acción.'

    def has_permission(self, request, view):
        return isinstance(request.user, PM_Profesional)


class EsCliente(BasePermission):
    """El autenticado debe ser un paciente (no un profesional ni un administrador)."""
    message = 'Debe iniciar sesión como paciente para realizar esta acción.'

    def has_permission(self, request, view):
        return isinstance(request.user, PmCliente)


def es_dueno_del_recurso(usuario, id_profesional_recurso):
    """
    Regla central de propiedad: un profesional solo puede operar sobre sus
    propios datos (perfil, documentos, especialidades).
    """
    return isinstance(usuario, PM_Profesional) and usuario.pk == int(id_profesional_recurso)
