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
