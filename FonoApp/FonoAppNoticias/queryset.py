from django.db import models
from django.utils import timezone

class FonoApp_Noticias_Queryset(models.QuerySet):
    
    def activas(self):
        """
        Retorna solo las noticias que no han sido eliminadas lógicamente.
        """
        return self.filter(estado=True)

    def con_detalles(self):
        """
        ¡Súper importante para el rendimiento! 
        Optimiza la consulta usando select_related (para traer los datos del usuario)
        y prefetch_related (para traer las imágenes). Evita el problema N+1.
        """
        return self.select_related('FonoApp_Administracion').prefetch_related('imagenes')

    def eliminar_logico(self, id_noticia):
        """
        Oculta la noticia sin borrarla de la base de datos.
        """
        filas_actualizadas = self.filter(id_noticia=id_noticia).update(estado=False)
        return filas_actualizadas > 0

    def crear_noticia(self, usuario, titulo, contenido, imagenes=None, **extra_fields):
        """
        Crea la noticia y asocia las imágenes (si las hay).
        Se asegura de que no se superen las 4 imágenes.
        """
        # 1. Validar el límite de imágenes antes de crear nada
        if imagenes and len(imagenes) > 4:
            raise ValueError("No se pueden asociar más de 4 imágenes a una noticia.")

        # 2. Crear la noticia principal
        noticia = self.create(
            FonoApp_Administracion=usuario,
            titulo=titulo,
            contenido=contenido,
            **extra_fields
        )

        # 3. Si vienen imágenes, guardarlas en la tabla relacionada
        if imagenes:
            # Importación local para evitar un error de "importación circular" con models.py
            from .models import FonoApp_Noticia_Imagen 
            
            # Usamos bulk_create para guardar todas las imágenes en 1 sola consulta SQL
            imagenes_objs = [
                FonoApp_Noticia_Imagen(noticia=noticia, imagen=img) 
                for img in imagenes
            ]
            FonoApp_Noticia_Imagen.objects.bulk_create(imagenes_objs)

        return noticia
    
    def editar_noticia(self, id_noticia, **datos_a_actualizar):
        """
        Actualiza los campos de texto de la noticia de forma masiva y eficiente.
        """
        # Por seguridad, evitamos que intenten actualizar al dueño o inyectar campos no válidos
        datos_a_actualizar.pop('FonoApp_Administracion', None)
        datos_a_actualizar.pop('imagenes_subidas', None)
        
        # Inyectamos la fecha actual manualmente ya que .update() ignora el auto_now=True
        datos_a_actualizar['fecha_actualizacion'] = timezone.now()
        
        # Filtramos por id_noticia y estado=True (para no editar noticias eliminadas lógicamente)
        filas_actualizadas = self.filter(id_noticia=id_noticia, estado=True).update(**datos_a_actualizar)
        
        return filas_actualizadas > 0
    
    def agregar_imagenes(self, id_noticia, nuevas_imagenes):
        """
        Agrega nuevas imágenes a una noticia existente, validando el límite máximo de 4.
        Retorna una tupla (exito_booleano, mensaje_string).
        """
        try:
            # Necesitamos la instancia para contar cuántas imágenes tiene actualmente
            noticia = self.get(id_noticia=id_noticia, estado=True)
        except models.ObjectDoesNotExist:
            return False, "Noticia no encontrada o inactiva."

        cantidad_actual = noticia.imagenes.count()
        
        # Validamos que la suma de las que ya existen + las nuevas no supere 4
        if cantidad_actual + len(nuevas_imagenes) > 4:
            return False, f"Límite excedido. La noticia ya tiene {cantidad_actual} imágenes y solo puedes tener un máximo de 4."

        from .models import FonoApp_Noticia_Imagen 
        
        # Usamos bulk_create para guardar todas las imágenes en 1 sola consulta SQL
        imagenes_objs = [
            FonoApp_Noticia_Imagen(noticia=noticia, imagen=img) 
            for img in nuevas_imagenes
        ]
        FonoApp_Noticia_Imagen.objects.bulk_create(imagenes_objs)
        
        return True, "Imágenes agregadas correctamente."