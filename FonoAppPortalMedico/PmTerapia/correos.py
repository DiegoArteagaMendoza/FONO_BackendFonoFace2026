"""
Correos que se envían al paciente sobre su plan de terapia.

Por ahora uno solo: el recordatorio cuando un periodo cierra sin todos sus
videos. Lo dispara el comando enviar_recordatorios_terapia, nunca una vista.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

from PmTerapia.periodos import rango_de_periodo

logger = logging.getLogger(__name__)


def _enlace_mi_terapia():
    """
    URL de "Mi terapia" en el portal del paciente.

    Lleva el hash porque el frontend usa hash routing (ver withHashLocation en
    app.config.ts): sin el '#', el hosting devolvería un 404 al abrir el enlace.
    """
    base = getattr(settings, 'FRONTEND_URL', 'http://localhost:4200').rstrip('/')
    return f'{base}/#/portalmedico/paciente/terapia'


def _texto_periodo(plan, numero):
    """"el 21/09/2026" para un plan diario; "del 15/09/2026 al 21/09/2026" para el resto."""
    desde, hasta = rango_de_periodo(plan.fecha_inicio, plan.periodicidad, numero)
    if desde == hasta:
        return f'el {desde:%d/%m/%Y}'
    return f'del {desde:%d/%m/%Y} al {hasta:%d/%m/%Y}'


def enviar_recordatorio_periodo(plan, numero, faltan):
    """
    Avisa al paciente de que un periodo de su plan terminó sin todos los videos.

    'faltan' son los nombres de los ejercicios sin video en ese periodo. Como
    en las citas, un fallo de envío se registra en el log y devuelve False; el
    comando que lo llama decide qué hacer con eso y sigue con el resto.
    """
    cliente = plan.cliente
    destinatario = (cliente.email_cliente or '').strip()

    if not destinatario:
        logger.warning('Plan %s sin correo de destino; no se envía recordatorio.', plan.pk)
        return False

    profesional = f'{plan.profesional.nombres_profesional} {plan.profesional.apellidos_profesional}'
    lista_faltan = '\n'.join(f'    - {nombre}' for nombre in faltan)

    asunto = 'Te faltaron videos de tu terapia'
    cuerpo = f"""Hola {cliente.nombres_cliente},

El periodo de tu plan de terapia con {profesional} que iba {_texto_periodo(plan, numero)}
terminó sin el video de estos ejercicios:

{lista_faltan}

Grabar tus ejercicios es la forma en que tu fonoaudiólogo puede ver cómo vas y
corregirte a tiempo. Puedes seguir con el periodo actual desde tu portal:

{_enlace_mi_terapia()}

Si tienes dudas sobre algún ejercicio, ahí mismo encontrarás el video de ejemplo
y las instrucciones.

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
        logger.exception('No se pudo enviar el recordatorio del plan %s', plan.pk)
        return False
