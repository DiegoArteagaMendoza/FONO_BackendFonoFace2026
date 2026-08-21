from django.db import models
from django.conf import settings
from FonoAppInformacion.queryset import FonoApp_Informacion_Queryset
from cloudinary.models import CloudinaryField # Importación necesaria

class FonoApp_Informacion(models.Model):
    
    # 1. Definimos el Enum usando TextChoices
    class CategoriaOpciones(models.TextChoices):
        PROMOCION = 'PO', 'Promocion'
        PREVENCION = 'PE', 'Prevencion'
        GENERAL = 'GE', 'general'
        FARMACOS = 'FA', 'farmacos'
        # SALUD = 'NI', 'ninos'
        # CUIDADOS = 'PO', 'profesores'
        # NUTRICION = 'CA', 'cantantesactores'
        # TIPS = 'LO', 'locutores'
        # Formato: VARIABLE_BD = 'VALOR_GUARDADO_EN_BD', 'Nombre legible para el usuario'

    id_informacion = models.AutoField("Codigo Informacion", primary_key=True)
    
    # Datos informacion
    titulo = models.CharField(max_length=150)
    
    # 2. Implementamos el campo categoría apuntando al Enum
    categoria = models.CharField(
        max_length=2, # Debe coincidir con el largo de 'SA', 'CU', etc.
        choices=CategoriaOpciones.choices,
        default=CategoriaOpciones.GENERAL,
        verbose_name="Categoría"
    )
    
    contenido = models.TextField(verbose_name="Cuerpo información")
    
    # Metadatos de control
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última actualización')
    estado = models.BooleanField(default=True, verbose_name='Activo') # Para borrado lógico
    
    # Datos Usuario que registro
    FonoApp_Administracion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='informaciones_registradas',
        verbose_name='Registrada por'
    )
    
    objects = FonoApp_Informacion_Queryset.as_manager()
    
    class Meta:
        db_table = 'FonoApp_Informacion'
        managed = True
        verbose_name = "Informacion"
        verbose_name_plural = "Informaciones"
        ordering = ['-fecha_creacion'] 
        
    def __str__(self):
        return f'{self.titulo} - {self.get_categoria_display()} ({self.fecha_creacion.strftime("%d/%m/%Y")})'

# =========================================================
# MODELO PARA MANEJAR LAS IMÁGENES (0 a 4)
# =========================================================
class FonoApp_Informacion_Imagen(models.Model):
    informacion = models.ForeignKey(
        FonoApp_Informacion, 
        on_delete=models.CASCADE, 
        related_name='imagenes' # Importante para el Serializer
    )
    
    # ACTUALIZACIÓN A CLOUDINARY
    # Reemplaza models.ImageField(upload_to='informacion/imagenes/', ...)
    imagen = CloudinaryField('Imagen', folder='informacion_imagenes')
    
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'FonoApp_Informacion_Imagen'
        verbose_name = 'Imagen de la Informacion'
        verbose_name_plural = 'Imágenes de la Informacion'

    def __str__(self):
        return f'Imagen de {self.informacion.titulo}'