from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import AccessToken

from PmMedico.models import Administrador, PM_Profesional


class PmMedicoJWTAuthentication(BaseAuthentication):
    """
    Autentica peticiones Bearer JWT de DOS orígenes distintos:

    1. Administradores: inician sesión en el proyecto principal FonoApp
       (FonoAppAdministracion.login_view), que firma el token con el claim
       estándar de SimpleJWT 'user_id'. Para que ese token sea válido AQUÍ,
       el SECRET_KEY de ambos proyectos debe ser idéntico (ver settings.py).
       Modelo de 3 roles de FonoApp (Usuario / Admin / SuperAdmin): aquí, en
       el Portal Médico, todas las acciones administrativas exigen al menos
       el rol Admin (is_staff); ver el permiso EsAdministrador. Gestión de
       Usuarios de FonoApp, en cambio, es exclusiva de SuperAdmin, pero ese
       endpoint vive en el otro proyecto (FonoApp), no aquí.

    2. Profesionales: inician sesión en este mismo proyecto (PmMedico.views.
       profesional_login), que firma el token con el claim propio 'id_profesional'.

    No se mezclan ambos universos de usuario en una sola tabla porque son
    conceptualmente distintos (administración de FonoApp vs. profesionales
    que se acreditan en el Portal Médico).
    """

    def authenticate(self, request):
        header = request.headers.get('Authorization')
        if not header or not header.startswith('Bearer '):
            return None

        try:
            token_str = header.split()[1]
            token = AccessToken(token_str)
        except Exception:
            raise AuthenticationFailed('Token inválido o expirado')

        id_administrador = token.get('user_id')
        id_profesional = token.get('id_profesional')

        if id_administrador is not None:
            try:
                administrador = Administrador.objects.get(pk=id_administrador)
            except Administrador.DoesNotExist:
                raise AuthenticationFailed('Administrador no encontrado')

            if not (administrador.is_active and administrador.estado):
                raise AuthenticationFailed('Cuenta de administrador inactiva')

            return (administrador, token)

        if id_profesional is not None:
            try:
                profesional = PM_Profesional.objects.get(pk=id_profesional)
            except PM_Profesional.DoesNotExist:
                raise AuthenticationFailed('Profesional no encontrado')

            if not profesional.estado_cuenta_profesional:
                raise AuthenticationFailed('Cuenta de profesional inactiva')

            return (profesional, token)

        raise AuthenticationFailed('El token no contiene una identidad reconocible')
