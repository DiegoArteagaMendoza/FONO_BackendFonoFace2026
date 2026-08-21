from django.db import models
from django.conf import settings
from FonoAppVoz.queryset import FonoApp_Voz_Queryset
from cloudinary.models import CloudinaryField # Importación necesaria

class CategoriaChoices(models.TextChoices):
    DEFINICION = 'DEFINICION', 'Definición'
    ANATOMIA = 'ANATOMIA', 'Anatomía'
    FISIOLOGIA = 'FISIOLOGIA', 'Fisiología'
    TRASTORNOS = 'TRASTORNOS', 'Trastornos de la Voz'
    IMPORTANCIA = 'IMPORTANCIA', 'Importancia del Cuidado'
    CURIOSIDADES = 'CURIOSIDADES', 'Curiosidades'

class FonoApp_Voz(models.Model):
    id_voz = models.AutoField("Código registro voz", primary_key=True)

    # Campo basado en el Enum de opciones
    categoria = models.CharField(
        max_length=20,
        choices=CategoriaChoices.choices,
        default=CategoriaChoices.DEFINICION,
        verbose_name="Categoría"
    )

    titulo = models.CharField(max_length=150, verbose_name="Título")
    contenido = models.TextField(verbose_name="Contenido informativo sobre la voz")
    
    # ACTUALIZACIÓN A CLOUDINARY
    # Reemplaza models.ImageField(upload_to='voz/imagenes/', null=True, blank=True, verbose_name="Imagen")
    img = CloudinaryField('Imagen', folder='voz_imagenes', null=True, blank=True)
    
    fuente = models.URLField(max_length=500, null=True, blank=True, verbose_name="Fuentes Científicas")
    estado = models.BooleanField(default=True, verbose_name="Activo") # 1 = activo / 0 = desactivado

    # Relación con el usuario administrador
    FonoApp_Administracion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='voz_registrada',
        verbose_name='Registrada por'
    )

    # Vinculación del QuerySet
    objects = FonoApp_Voz_Queryset.as_manager()

    class Meta:
        db_table = 'FonoApp_Voz'
        managed = True
        verbose_name = "Voz"
        verbose_name_plural = "Voz"
        ordering = ['id_voz']

    def __str__(self):
        return f'{self.titulo} ({self.get_categoria_display()})'