"""
Correo con el resultado de una autoevaluación, a pedido del propio paciente.

A diferencia de PmCita/correos.py, aquí el destinatario no sale de ninguna
ficha guardada: el paciente lo escribe recién al ver su resultado, en un
formulario aparte que no forma parte de la respuesta del test. Por eso esta
función recibe el correo como parámetro y en ningún momento lo guarda en el
modelo ni en ningún otro lugar; solo se usa para el envío en curso.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def enviar_resultado_diagnostico(respuesta, destinatario):
    """
    Envía por correo el resultado ya calculado de una respuesta de diagnóstico.

    Igual que enviar_confirmacion_reserva: nunca interrumpe el flujo del
    frontend por un problema de correo (SMTP caído, dirección inválida). Si
    falla, se registra en el log y se devuelve False; el resultado ya se
    mostró en pantalla de todas formas.
    """
    destinatario = (destinatario or '').strip()
    if not destinatario:
        logger.warning('Envío de resultado %s sin correo de destino.', respuesta.pk)
        return False

    formulario = respuesta.formulario
    asunto = f'Tu resultado de "{formulario.nombre}"'

    lineas = [
        f'Hola {respuesta.paciente_nombre},',
        '',
        f'Este es el resultado de tu autoevaluación "{formulario.nombre}":',
        '',
        f'Puntaje total: {respuesta.puntaje_total}',
    ]

    interpretacion_total = respuesta.interpretacion_total or {}
    if interpretacion_total.get('etiqueta'):
        lineas.append(f'Interpretación: {interpretacion_total["etiqueta"]}')
        if interpretacion_total.get('descripcion'):
            lineas.append(interpretacion_total['descripcion'])

    detalle_subescalas = respuesta.detalle_subescalas or []
    if detalle_subescalas:
        lineas.append('')
        lineas.append('Detalle por sección:')
        for subescala in detalle_subescalas:
            interpretacion = subescala.get('interpretacion') or {}
            etiqueta = f' ({interpretacion["etiqueta"]})' if interpretacion.get('etiqueta') else ''
            lineas.append(f'- {subescala.get("subescala", "")}: {subescala.get("puntaje", 0)}{etiqueta}')

    lineas.append('')
    lineas.append('Este resultado es solo referencial y no reemplaza una evaluación clínica.')
    lineas.append('')
    lineas.append('Portal Vocare UBB — Universidad del Bío-Bío')

    try:
        send_mail(
            subject=asunto,
            message='\n'.join(lineas),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario],
            fail_silently=False,
        )
        return True
    except Exception:
        # exception() incluye la traza, que hace falta para diagnosticar un SMTP
        # mal configurado; el usuario no ve nada de esto.
        logger.exception('No se pudo enviar el resultado de la respuesta %s', respuesta.pk)
        return False
