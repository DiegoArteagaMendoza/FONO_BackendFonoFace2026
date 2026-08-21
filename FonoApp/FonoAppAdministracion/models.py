from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from FonoAppAdministracion.queryset import FonoAPP_Manager, FonoApp_Banner_Queryset
from cloudinary.models import CloudinaryField # Importación necesaria

class FonoApp_Administracion(AbstractBaseUser, PermissionsMixin):
    id_usuario = models.AutoField("Codigo registro usuario", primary_key=True)
    nombre = models.CharField(max_length=50)
    rut = models.CharField(max_length=12, unique=True)
    email = models.EmailField(unique=True)
    tipo = models.BooleanField(default=False)
    estado = models.BooleanField(default=True) # 1 = activo
    is_staff = models.BooleanField(default=False, blank=True)
    is_active = models.BooleanField(default=True, blank=True)
    last_conection = models.DateTimeField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'rut']
    
    # Manager basado en BaseUserManager (ver queryset.py) para soportar
    # 'python manage.py createsuperuser' además de los métodos de negocio.
    objects = FonoAPP_Manager()
    
    class Meta:
        db_table = 'FonoApp_Administracion'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f'{self.nombre} ({self.rut})'
    
# ===========================================
# MODELO PARA MANEJAR INFORMACIÓN DEL BANNER
# ===========================================
    
class FonoApp_Banner_Inicio(models.Model):
    id_banner = models.AutoField("Código registro banner", primary_key=True)
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField(verbose_name='Cuerpo del banner')
    
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última actualización')
    estado = models.BooleanField(default=True, verbose_name='Activo')
    
    FonoApp_Administracion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='banners_registrados',
        verbose_name='Registrado por'
    )

    # VINCULACIÓN CORREGIDA: Usamos su mánager exclusivo
    objects = FonoApp_Banner_Queryset.as_manager()

    class Meta:
        db_table = 'FonoApp_Banner'
        managed = True
        verbose_name = "Banner"
        verbose_name_plural = "Banners"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'{self.titulo} (# {self.id_banner})'
    

class FonoApp_Banner_Inicio_Imagenes(models.Model):
    banner = models.ForeignKey(
        FonoApp_Banner_Inicio,
        on_delete=models.CASCADE,
        related_name='imagenes'
    )
    
    # ACTUALIZACIÓN A CLOUDINARY
    # Reemplaza models.ImageField(upload_to='banner/imagenes/')
    imagen = CloudinaryField('imagen', folder='banner_imagenes') 
    
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'FonoApp_Banner_Imagen'
        verbose_name = 'Imagen del banner'
        verbose_name_plural = 'Imágenes del banner'

    def __str__(self):
        return f'Imagen de {self.banner.titulo}'