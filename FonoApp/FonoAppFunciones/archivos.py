"""
Utilidades para los campos de archivo almacenados en Cloudinary.

Existe una copia gemela en FonoAppPortalMedico/Security/archivos.py: los dos
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
