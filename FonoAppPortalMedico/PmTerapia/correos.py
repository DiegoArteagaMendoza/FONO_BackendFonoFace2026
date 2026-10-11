"""
Correos que se envían al paciente sobre su plan de terapia.

Son dos: el recordatorio cuando un periodo cierra sin todos sus videos (lo
dispara el comando enviar_recordatorios_terapia) y el aviso de que su
fonoaudiólogo le dejó retroalimentación en un video.

Ninguno interrumpe lo que estaba pasando: si el envío falla se registra en el
log y se devuelve False. Que un correo no salga no puede costarle al
fonoaudiólogo la retroalimentación que acaba de escribir.
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


def _enviar(asunto, cuerpo, destinatario, que_es):
    """
    Envía y devuelve si salió. 'que_es' solo se usa para el log cuando falla.
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
        logger.exception('No se pudo enviar %s', que_es)
        return False


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

    return _enviar(asunto, cuerpo, destinatario, f'el recordatorio del plan {plan.pk}')


def enviar_aviso_retroalimentacion(video):
    """
    Avisa al paciente de que su fonoaudiólogo le comentó un video.

    El texto va completo dentro del correo: es corto por naturaleza y el
    paciente suele leerlo en el teléfono, donde abrir el portal para ver dos
    líneas es un trámite. El enlace queda igual para quien quiera ver el video
    junto al comentario.

    Se manda cada vez que el fonoaudiólogo guarda un texto, también cuando
    corrige lo que ya había escrito: una corrección puede cambiar por completo
    la indicación, y enterarse tarde es peor que recibir un correo de más.
    """
    plan = video.plan_ejercicio.plan
    cliente = plan.cliente
    destinatario = (cliente.email_cliente or '').strip()

    if not destinatario:
        logger.warning('Video %s sin correo de destino; no se avisa la retroalimentación.', video.pk)
        return False

    profesional = f'{plan.profesional.nombres_profesional} {plan.profesional.apellidos_profesional}'
    ejercicio = video.plan_ejercicio.ejercicio.nombre

    asunto = f'{profesional} comentó tu video de terapia'
    cuerpo = f"""Hola {cliente.nombres_cliente},

{profesional} revisó el video de "{ejercicio}" que enviaste el
{video.fecha_subida:%d/%m/%Y} y te dejó este comentario:

{video.retroalimentacion}

Puedes verlo junto al video en tu portal:

{_enlace_mi_terapia()}

Portal Médico Vocare UBB — Universidad del Bío-Bío
"""

    return _enviar(asunto, cuerpo, destinatario, f'el aviso de retroalimentación del video {video.pk}')
