"""
Validadores de seguridad/formato reutilizados por los modelos y serializers de PmMedico.
"""
import os
import re

from django.conf import settings
from django.core.exceptions import ValidationError


def _limpiar_rut(rut):
    return re.sub(r'[.\-\s]', '', rut or '').upper()


def validar_rut_chileno(rut):
    """
    Valida formato y dígito verificador de un RUT chileno.
    Acepta con o sin puntos/guión (ej: '12.345.678-5' o '123456785').
    """
    limpio = _limpiar_rut(rut)

    if not re.fullmatch(r'\d{7,8}[0-9K]', limpio):
        raise ValidationError('El RUT no tiene un formato válido (ej: 12345678-5).')

    cuerpo, dv_ingresado = limpio[:-1], limpio[-1]

    suma = 0
    multiplo = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * multiplo
        multiplo = multiplo + 1 if multiplo < 7 else 2

    resto = 11 - (suma % 11)
    dv_esperado = {11: '0', 10: 'K'}.get(resto, str(resto))

    if dv_ingresado != dv_esperado:
        raise ValidationError('El RUT ingresado no es válido (dígito verificador incorrecto).')


def validar_telefono(telefono):
    """
    Acepta números chilenos con o sin el prefijo +56 (celulares y fijos).
    Ej: '+56912345678', '912345678', '221234567'.
    """
    limpio = re.sub(r'[\s\-]', '', telefono or '')
    if not re.fullmatch(r'(\+?56)?[2-9]\d{7,8}', limpio):
        raise ValidationError('El teléfono no tiene un formato válido (ej: +56912345678).')


EXTENSIONES_DOCUMENTO_PERMITIDAS = ('.pdf', '.jpg', '.jpeg', '.png')


def validar_archivo_documento(archivo):
    """
    Restringe los documentos de respaldo a formatos y tamaño seguros para evitar
    la subida de ejecutables u otros archivos maliciosos.
    """
    _, extension = os.path.splitext(archivo.name)
    if extension.lower() not in EXTENSIONES_DOCUMENTO_PERMITIDAS:
        raise ValidationError(
            f'Formato de archivo no permitido. Use uno de: {", ".join(EXTENSIONES_DOCUMENTO_PERMITIDAS)}.'
        )

    max_mb = getattr(settings, 'PM_MEDICO_DOCUMENTO_MAX_MB', 5)
    if archivo.size > max_mb * 1024 * 1024:
        raise ValidationError(f'El archivo supera el tamaño máximo permitido de {max_mb}MB.')
