from django.db import models
from django.conf import settings
from FonoAppCuidados.queryset import FonoApp_Cuidados_Queryset
from cloudinary.models import CloudinaryField # Importación necesaria

class PublicoChoices(models.TextChoices):
    NINOS = 'NIÑOS', 'Niños'
    PROFESORES = 'PROFESORES', 'Profesores'
    CANTANTES_ACTORES = 'CANTANTES_ACTORES', 'Cantantes y/o Actores'
    LOCUTORES = 'LOCUTORES', 'Locutores'
    GENERAL = 'PUBLICO_GENERAL', 'Público General'

class FonoApp_Cuidados(models.Model):
    id_cuidado = models.AutoField("Código registro cuidado", primary_key=True)
    
    # Campo basado en el Enum de opciones
    publico = models.CharField(
        max_length=20,
        choices=PublicoChoices.choices,
        default=PublicoChoices.GENERAL,
        verbose_name="Público Objetivo"
    )
    
    titulo = models.CharField(max_length=150, verbose_name="Título")
    contenido = models.TextField(verbose_name="Contenido de cuidados")
    
    # ACTUALIZACIÓN A CLOUDINARY
    # Reemplaza models.ImageField(upload_to='cuidados/imagenes/', ...)
    img = CloudinaryField('Imagen', folder='cuidados_imagenes', null=True, blank=True)
    
    fuente = models.URLField(max_length=500, null=True, blank=True, verbose_name="Fuentes Científicas")
    estado = models.BooleanField(default=True, verbose_name="Activo") # 1 = activo / 0 = desactivado
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True, verbose_name="Fecha de creación")
    
    # Relación con el usuario administrador
    FonoApp_Administracion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cuidados_registrados',
        verbose_name='Registrada por'
    )
    
    # Vinculación del QuerySet
    objects = FonoApp_Cuidados_Queryset.as_manager()
    
    class Meta:
        db_table = 'FonoApp_Cuidados'
        managed = True
        verbose_name = "Cuidado"
        verbose_name_plural = "Cuidados"
        ordering = ['id_cuidado']
        
    def __str__(self):
        return f'{self.titulo} ({self.get_publico_display()})'