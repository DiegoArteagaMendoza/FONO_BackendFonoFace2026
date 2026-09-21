"""
Utilidades para los campos de archivo almacenados en Cloudinary.

Existe una copia gemela en FonoApp/FonoAppFunciones/archivos.py: los dos
proyectos Django no comparten código, así que el cambio que se haga aquí debe
replicarse allá.
"""


def url_absoluta(recurso):
    """
    URL https completa de un CloudinaryField, lista para el frontend.

    DRF serializa un CloudinaryField como su public_id (por ejemplo
    'noticias_imagenes/abc'), que no es una URL: el frontend, al no verla
    absoluta, le antepondría su backendUrl/media/ y quedaría rota. Este helper
    se usa en el to_representation de cada serializer con archivos para
    entregar la URL real (CloudinaryResource.url la construye con el
    CLOUD_NAME configurado y secure=True).

    Si el valor no es un recurso de Cloudinary (registros antiguos guardados
    como texto por el FileField anterior), se devuelve tal cual: esas rutas
    /media/ ya las sabe completar el frontend.
    """
    if not recurso:
        return None

    url = getattr(recurso, 'url', None)
    return url or str(recurso)

def borrar_de_cloudinary(recurso):
    """
    Elimina de Cloudinary el archivo de un CloudinaryField.

    NO se puede usar `campo.delete(save=False)` como con un FileField: el valor
    de un CloudinaryField es un CloudinaryResource, que no tiene ese método y
    lanza AttributeError. Hay que llamar al uploader con el public_id y el
    resource_type correcto ('video' y 'raw' no se borran con el 'image' por
    defecto).

    Devuelve True si Cloudinary confirma el borrado. Un archivo que ya no
    existe cuenta como éxito: el objetivo es que no quede, y reintentarlo no
    debe hacer fallar al comando de limpieza.

    Los registros antiguos guardados como texto por el FileField anterior no
    están en Cloudinary; se ignoran devolviendo False.
    """
    if not recurso:
        return False

    public_id = getattr(recurso, 'public_id', None)
    if not public_id:
        # Valor heredado (ruta de texto en disco), no hay nada que borrar aquí.
        return False

    import cloudinary.uploader

    tipo = getattr(recurso, 'resource_type', None) or 'image'
    resultado = cloudinary.uploader.destroy(public_id, resource_type=tipo, invalidate=True)
    return resultado.get('result') in ('ok', 'not found')


def guardar_o_400(objeto, **campos):
    """
    Guarda un serializer o una instancia con CloudinaryField traduciendo el
    rechazo del proveedor en un 400.

    Acepta las dos cosas porque hay vistas que construyen el modelo a mano (el
    video de progreso, cuyo periodo y dueño los pone el servidor) y otras que
    pasan por un ModelSerializer. En ambos casos el archivo se sube dentro de
    save(), y ahí es donde Cloudinary puede decir que no.

    El archivo no pasa por el almacenamiento de Django: CloudinaryField lo sube
    con su propio SDK dentro de save(), y si Cloudinary lo rechaza —un .mp4 que
    en realidad no es un video, un archivo truncado— lanza una excepción que
    sin esto sale como error 500 y una página de Django en la cara de quien
    subió. El serializer valida extensión, peso y duración declarada, pero no
    puede saber si el contenido es realmente reproducible: eso solo lo dice el
    proveedor.

    Vive aquí y no en una app porque lo necesitan todas las vistas que suben
    video (síntomas, ejemplos de ejercicios, progreso de terapia).

    Devuelve la Response de error, o None si guardó bien.
    """
    from django.db import transaction
    from rest_framework import status
    from rest_framework.response import Response
    # Error base de Cloudinary: cubre BadRequest (archivo ilegible) y también
    # los fallos de red o de cuota, que tampoco deben salir como 500 mudo.
    from cloudinary.exceptions import Error as CloudinaryError

    try:
        # Savepoint: la subida falla a mitad del INSERT, y sin esto el fallo
        # deja rota cualquier transacción que envuelva a la vista (una prueba,
        # o ATOMIC_REQUESTS si algún día se activa). Con el savepoint se
        # revierte solo este intento y lo de afuera sigue usable.
        with transaction.atomic():
            objeto.save(**campos)
        return None
    except CloudinaryError:
        return Response(
            {'video': 'No pudimos procesar el archivo. Asegúrate de que sea un video que se '
                      'reproduzca correctamente e inténtalo de nuevo.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
