"""
Correos del newsletter de noticias.

Son dos: la confirmación cuando alguien se suscribe (o reactiva su
suscripción) y el aviso a todos los suscriptores activos cuando se publica una
noticia nueva. Ambos llevan un enlace para darse de baja.

El enlace de baja no expone el id de la suscripción: lleva el correo firmado
con la SECRET_KEY (django.core.signing), así nadie puede dar de baja a otro
inventando un número. No vence: un correo viejo tiene que seguir sirviendo
para salir del newsletter.

Igual que FonoAppDiagnostico/correos.py, nada de esto interrumpe el flujo que
lo llamó: si el SMTP falla, se registra en el log y la suscripción o la
noticia quedan guardadas de todas formas.
"""

import logging
from urllib.parse import quote

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMessage, get_connection

from FonoAppNoticias.models import FonoApp_Newsletter

logger = logging.getLogger(__name__)

_SALT_BAJA = 'FonoAppNoticias.newsletter.baja'

# Largo máximo del extracto de la noticia que va en el aviso; el resto se lee
# en el portal siguiendo el enlace.
_LARGO_EXTRACTO = 400

_FIRMA = 'Portal Vocare UBB — Universidad del Bío-Bío'


def token_baja(email):
    """Token firmado que identifica al suscriptor en el enlace de baja."""
    return signing.dumps(email, salt=_SALT_BAJA)


def email_desde_token(token):
    """Devuelve el correo de un token de baja, o None si es inválido o fue alterado."""
    try:
        return signing.loads(token, salt=_SALT_BAJA)
    except signing.BadSignature:
        return None


def _base_frontend():
    """
    Base del portal público. Los enlaces llevan el hash porque el frontend usa
    hash routing: sin el '#', el hosting devolvería un 404 al abrirlos.
    """
    return getattr(settings, 'FRONTEND_URL', 'http://localhost:4200').rstrip('/') + '/#'


def _enlace_baja(email):
    """URL de la página de baja del portal, que confirma la baja contra la API."""
    return f'{_base_frontend()}/portal/noticias/newsletter/baja?token={quote(token_baja(email))}'


def _enlace_noticia(noticia):
    """URL de la noticia en el portal público."""
    return f'{_base_frontend()}/portal/noticias/{noticia.id_noticia}'


def _extracto(texto):
    texto = (texto or '').strip()
    if len(texto) <= _LARGO_EXTRACTO:
        return texto
    return texto[:_LARGO_EXTRACTO].rsplit(' ', 1)[0] + '…'


def enviar_confirmacion_suscripcion(email):
    """
    Confirma al visitante que quedó suscrito al newsletter.

    Devuelve si el correo salió; un fallo solo queda en el log.
    """
    cuerpo = f"""Hola,

Tu correo quedó suscrito al newsletter del Portal Vocare UBB. Desde ahora te
avisaremos cada vez que publiquemos una noticia nueva.

Si no fuiste tú, o ya no quieres recibir estos avisos, puedes darte de baja aquí:

{_enlace_baja(email)}

{_FIRMA}
"""
    try:
        EmailMessage(
            subject='Te suscribiste al newsletter de Vocare UBB',
            body=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        ).send(fail_silently=False)
        return True
    except Exception:
        # exception() incluye la traza, que hace falta para diagnosticar un SMTP
        # mal configurado; el visitante no ve nada de esto.
        logger.exception('No se pudo enviar la confirmación de suscripción al newsletter')
        return False


def enviar_aviso_noticia(noticia):
    """
    Avisa a cada suscriptor activo que se publicó una noticia nueva.

    Se manda un correo por suscriptor (no uno con todos en copia): cada uno
    lleva su propio enlace de baja y nadie ve las direcciones de los demás.
    Todos salen por una sola conexión SMTP para no abrir una por correo.

    Devuelve (enviados, fallidos). Un fallo con un destinatario no corta el
    envío a los demás.
    """
    destinatarios = list(
        FonoApp_Newsletter.objects.activas().values_list('email', flat=True)
    )
    if not destinatarios:
        return 0, 0

    asunto = f'Nueva noticia en Vocare UBB: {noticia.titulo}'
    enlace_noticia = _enlace_noticia(noticia)
    extracto = _extracto(noticia.contenido)

    enviados = 0
    fallidos = 0
    try:
        conexion = get_connection(fail_silently=False)
        conexion.open()
    except Exception:
        logger.exception('No se pudo abrir la conexión SMTP para el aviso de la noticia %s', noticia.pk)
        return 0, len(destinatarios)

    try:
        for email in destinatarios:
            cuerpo = f"""Hola,

Publicamos una noticia nueva en el Portal Vocare UBB:

{noticia.titulo}

{extracto}

Léela completa aquí:

{enlace_noticia}

--
Recibes este correo porque te suscribiste al newsletter de Vocare UBB.
Para dejar de recibirlo: {_enlace_baja(email)}

{_FIRMA}
"""
            try:
                EmailMessage(
                    subject=asunto,
                    body=cuerpo,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email],
                    connection=conexion,
                ).send(fail_silently=False)
                enviados += 1
            except Exception:
                fallidos += 1
                logger.exception('No se pudo enviar el aviso de la noticia %s a un suscriptor', noticia.pk)
    finally:
        conexion.close()

    if fallidos:
        logger.warning(
            'Aviso de la noticia %s: %s enviado(s), %s fallido(s).', noticia.pk, enviados, fallidos
        )
    return enviados, fallidos
