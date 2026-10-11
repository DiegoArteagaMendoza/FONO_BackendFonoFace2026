import os
from io import BytesIO
from PIL import Image
from django.db import models
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

def _convertir_a_webp(img):
    """
    Convierte un archivo de imagen subido a WebP y lo devuelve listo para guardar.

    Devuelve un SimpleUploadedFile y NO un ContentFile, aunque para un FileField
    ambos servirían. CloudinaryField.pre_save solo sube a la nube si el valor es
    una instancia de UploadedFile; con cualquier otro File se va por el else y
    guarda str(valor) en la columna, que para un ContentFile es literalmente
    'Raw content'. El resultado era una fila apuntando a ese texto y la imagen
    perdida, sin ningún error visible.
    """
    imagen_pil = Image.open(img)

    # Asegurar compatibilidad de color (WebP soporta RGBA para transparencias de PNG)
    # Si viene en modo Paleta (P) o CMYK, lo pasamos a RGBA o RGB
    if imagen_pil.mode not in ("RGB", "RGBA"):
        imagen_pil = imagen_pil.convert("RGBA")

    buffer = BytesIO()
    imagen_pil.save(buffer, format="WEBP", quality=85)

    nombre_base = os.path.splitext(img.name)[0]
    nombre_webp = f"{nombre_base}.webp"

    return SimpleUploadedFile(nombre_webp, buffer.getvalue(), content_type='image/webp')


class FonoApp_Informacion_Queryset(models.QuerySet):

    # =========================================================
    # MÉTODOS DE BÚSQUEDA Y FILTRO
    # =========================================================

    def activas(self):
        """
        Retorna solo los registros que no han sido eliminados lógicamente.
        """
        return self.filter(estado=True)

    def con_detalles(self):
        """
        ¡Crucial para el rendimiento! Trae al autor (select_related) y 
        a las imágenes (prefetch_related) en la misma consulta para evitar el N+1.
        """
        return self.select_related('FonoApp_Administracion').prefetch_related('imagenes')

    def por_categoria(self, categoria_codigo):
        """
        Filtra por el código de la categoría (Ej: 'SA' para Salud Animal).
        """
        return self.filter(categoria=categoria_codigo)


    # =========================================================
    # MÉTODOS DE CREACIÓN, EDICIÓN Y ELIMINACIÓN
    # =========================================================

    def crear_informacion(self, usuario, titulo, categoria, contenido, imagenes=None, **extra_fields):
        """
        Crea el registro y asocia hasta 4 imágenes convirtiéndolas a WebP.
        """
        # 1. Validar límite de imágenes
        if imagenes and len(imagenes) > 4:
            raise ValueError("No se pueden asociar más de 4 imágenes.")

        # 2. Crear registro principal
        informacion = self.create(
            FonoApp_Administracion=usuario,
            titulo=titulo,
            categoria=categoria,
            contenido=contenido,
            **extra_fields
        )

        # 3. Guardar imágenes si existen (Convirtiendo a WebP)
        if imagenes:
            from .models import FonoApp_Informacion_Imagen

            for img in imagenes:
                archivo_webp = _convertir_a_webp(img)

                # Crear la instancia (esto guarda el archivo físico en la carpeta upload_to)
                FonoApp_Informacion_Imagen.objects.create(
                    informacion=informacion,
                    imagen=archivo_webp
                )

        return informacion

    def editar_informacion(self, id_informacion, **datos_a_actualizar):
        """
        Actualiza los campos de texto del registro de forma masiva y eficiente.
        Ejemplo de uso: .editar_informacion(1, titulo="Nuevo", categoria="CU")
        """
        # Limpiamos datos que no deberían actualizarse por esta vía (por seguridad)
        datos_a_actualizar.pop('FonoApp_Administracion', None)
        datos_a_actualizar.pop('imagenes_subidas', None) # Las imágenes se manejan aparte
        
        # 2. Inyectamos la fecha y hora actual manualmente para el campo de actualización
        datos_a_actualizar['fecha_actualizacion'] = timezone.now()
        
        # El update() retorna el número de filas afectadas (1 si fue exitoso, 0 si falló)
        filas_actualizadas = self.filter(id_informacion=id_informacion, estado=True).update(**datos_a_actualizar)
        
        return filas_actualizadas > 0

    def eliminar_logico(self, id_informacion):
        """
        Oculta el registro cambiando estado=False en lugar de borrarlo de la BD.
        """
        filas_actualizadas = self.filter(id_informacion=id_informacion).update(estado=False)
        return filas_actualizadas > 0

    def agregar_imagenes(self, id_informacion, nuevas_imagenes):
        """
        Agrega nuevas imágenes (convertidas a WebP) a un registro existente,
        validando que no se supere el máximo de 4 imágenes.
        Retorna una tupla (exito_booleano, mensaje_string).
        """
        try:
            informacion = self.get(id_informacion=id_informacion, estado=True)
        except models.ObjectDoesNotExist:
            return False, "Información no encontrada o inactiva."

        cantidad_actual = informacion.imagenes.count()

        if cantidad_actual + len(nuevas_imagenes) > 4:
            return False, f"Límite excedido. El registro ya tiene {cantidad_actual} imágenes y solo puedes tener un máximo de 4."

        from .models import FonoApp_Informacion_Imagen

        for img in nuevas_imagenes:
            archivo_webp = _convertir_a_webp(img)
            FonoApp_Informacion_Imagen.objects.create(informacion=informacion, imagen=archivo_webp)

        return True, "Imágenes agregadas correctamente."