"""
Correos que se envían al paciente sobre sus citas.

El más importante es el de confirmación: lleva el código de seguimiento, que es
la única forma de gestionar la hora para quien reservó sin cuenta.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _enlace_seguimiento(codigo):
    """
    URL de la pantalla de seguimiento con el código ya puesto.

    Lleva el hash porque el frontend usa hash routing (ver withHashLocation en
    app.config.ts): sin el '#', el hosting devolvería un 404 al abrir el enlace.
    """
    base = getattr(settings, 'FRONTEND_URL', 'http://localhost:4200').rstrip('/')
    return f'{base}/#/portalmedico/cita/seguimiento?codigo={codigo}'


def enviar_confirmacion_reserva(cita):
    """
    Avisa al paciente de que su hora quedó reservada y le entrega el código.

    Nunca interrumpe la reserva: si el correo falla (SMTP caído, dirección
    inválida), se registra en el log y la cita sigue creada. Perder la cita por
    un problema de correo sería mucho peor que quedarse sin el aviso, y el
    código igual queda guardado y visible en pantalla.
    """
    cliente = cita.cliente
    destinatario = (cliente.email_cliente or '').strip()

    if not destinatario:
        logger.warning('Cita %s sin correo de destino; no se envía confirmación.', cita.pk)
        return False

    fecha = cita.fecha_hora.strftime('%d/%m/%Y a las %H:%M')
    profesional = f'{cita.profesional.nombres_profesional} {cita.profesional.apellidos_profesional}'

    asunto = f'Tu hora quedó reservada — código {cita.codigo_seguimiento}'
    cuerpo = f"""Hola {cliente.nombres_cliente},

Tu hora con {profesional} quedó reservada para el {fecha}.

Tu código de seguimiento es:

    {cita.codigo_seguimiento}

Con ese código puedes ver el detalle de tu hora, cambiar la fecha o cancelarla,
sin necesidad de tener una cuenta. Ingresa aquí y escríbelo:

{_enlace_seguimiento(cita.codigo_seguimiento)}

Ten presente que los cambios y las cancelaciones deben hacerse con al menos
{_horas_anticipacion()} horas de anticipación.

Guarda este correo: el código es personal y es lo único que se necesita para
gestionar tu hora.

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
        # mal configurado; el usuario no ve nada de esto.
        logger.exception('No se pudo enviar la confirmación de la cita %s', cita.pk)
        return False


def _horas_anticipacion():
    from PmCita.models import HORAS_MINIMAS_ANTICIPACION

    return HORAS_MINIMAS_ANTICIPACION
