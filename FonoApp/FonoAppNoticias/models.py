from django.db import models
from django.conf import settings
from FonoAppNoticias.queryset import FonoApp_Noticias_Queryset

class FonoApp_Noticias(models.Model):
    id_noticia = models.AutoField("Codigo noticia", primary_key=True)
    
    # Datos de la noticia
    titulo = models.CharField(max_length=150)
    contenido = models.TextField(verbose_name='Cuerpo de la noticia') # El texto de la noticia
    
    # Metadatos de control
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última actualización')
    estado = models.BooleanField(default=True, verbose_name='Activo') # Para borrado lógico, igual que en Usuarios
    
    # Datos Usuario que registro
    FonoApp_Administracion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='noticias_registradas',
        verbose_name='Registrada por'
    )
    
    objects = FonoApp_Noticias_Queryset.as_manager()
    
    class Meta:
        db_table = 'FonoApp_Noticias'
        managed = True
        verbose_name = "Noticia"
        verbose_name_plural = "Noticias"
        ordering = ['-fecha_creacion'] # Por defecto, ordena de la más nueva a la más vieja
        
    def __str__(self):
        return f'{self.titulo} - {self.fecha_creacion.strftime("%d/%m/%Y")}'


# =========================================================
# MODELO PARA LAS SUSCRIPCIONES AL NEWSLETTER
# =========================================================
class FonoApp_Newsletter(models.Model):
    id_suscripcion = models.AutoField("Codigo suscripcion", primary_key=True)
    email = models.EmailField(max_length=254, unique=True, verbose_name='Correo electrónico')
    fecha_suscripcion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de suscripción')
    estado = models.BooleanField(default=True, verbose_name='Activo') # Para borrado lógico / desuscripción

    class Meta:
        db_table = 'FonoApp_Newsletter'
        managed = True
        verbose_name = "Suscripción al Newsletter"
        verbose_name_plural = "Suscripciones al Newsletter"
        ordering = ['-fecha_suscripcion']

    def __str__(self):
        return f'{self.email} - {self.fecha_suscripcion.strftime("%d/%m/%Y")}'


# =========================================================
# MODELO PARA MANEJAR LAS IMÁGENES (0 a 4)
# =========================================================
class FonoApp_Noticia_Imagen(models.Model):
    noticia = models.ForeignKey(
        FonoApp_Noticias, 
        on_delete=models.CASCADE, 
        related_name='imagenes' # Importante para el Serializer
    )
    imagen = models.ImageField(upload_to='noticias/imagenes/', verbose_name='Imagen')
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'FonoApp_Noticia_Imagen'
        verbose_name = 'Imagen de Noticia'
        verbose_name_plural = 'Imágenes de Noticias'

    def __str__(self):
        return f'Imagen de {self.noticia.titulo}'