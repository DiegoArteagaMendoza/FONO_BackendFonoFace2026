"""
Correos que salen de la administración de profesionales.

Por ahora uno: el aviso al paciente cuando su hora se cancela porque el
profesional fue dado de baja. Lo dispara la vista que deshabilita la cuenta.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _enlace_directorio():
    """
    URL del directorio de fonoaudiólogos, para que el paciente pueda reservar
    con otro sin tener que buscar por dónde entrar.

    Lleva el hash porque el frontend usa hash routing (ver withHashLocation en
    app.config.ts): sin el '#', el hosting devolvería un 404.
    """
    base = getattr(settings, 'FRONTEND_URL', 'http://localhost:4200').rstrip('/')
    return f'{base}/#/portalmedico/directorio'


def enviar_aviso_baja_profesional(cita, motivo=''):
    """
    Le avisa al paciente que su hora quedó cancelada porque el profesional ya
    no está disponible.

    Es el correo que vuelve honesta la baja administrativa: sin él, el paciente
    se enteraría al llegar a una cita que ya no existe. Un fallo de envío se
    registra y devuelve False, sin interrumpir el resto de los avisos.
    """
    cliente = cita.cliente
    destinatario = (cliente.email_cliente or '').strip()

    if not destinatario:
        logger.warning('Cita %s sin correo de destino; no se avisa la cancelación por baja.', cita.pk)
        return False

    profesional = f'{cita.profesional.nombres_profesional} {cita.profesional.apellidos_profesional}'
    fecha = cita.fecha_hora.strftime('%d/%m/%Y a las %H:%M')
    explicacion = f'\nMotivo: {motivo}\n' if motivo else ''

    asunto = 'Tu hora fue cancelada'
    cuerpo = f"""Hola {cliente.nombres_cliente},

Lamentamos avisarte que tu hora del {fecha} con {profesional} quedó cancelada:
el profesional ya no está atendiendo en el portal.
{explicacion}
No tienes que hacer nada con esa hora. Si quieres reagendar con otro
fonoaudiólogo, aquí puedes ver quiénes tienen horas disponibles:

{_enlace_directorio()}

Disculpa las molestias.

Portal Médico Vocare UBB — Universidad del Bío-Bío
"""

    try:
        send_mail(
            subject=asunto,
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario],
            fail_silently=False,
        )
        return True
    except Exception:
        # exception() incluye la traza, que hace falta para diagnosticar un SMTP
        # mal configurado; el paciente no ve nada de esto.
        logger.exception('No se pudo avisar la cancelación de la cita %s', cita.pk)
        return False
