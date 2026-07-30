from django.db import models
from django.conf import settings
from .queryset import FonoApp_InfoGeneral_Queryset

class FonoApp_InfoGeneral(models.Model):
    id_info = models.AutoField("Código registro información", primary_key=True)
    
    # Agrupación y búsqueda
    seccion = models.CharField(max_length=50, help_text="Ej: inicio, portal_cliente, footer")
    clave = models.CharField(max_length=50, unique=True, help_text="Identificador único. Ej: inicio_cuidados")
    
    # Contenido dinámico
    titulo = models.CharField(max_length=150, blank=True, null=True, verbose_name="Título a mostrar")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Cuerpo del texto")
    enlace = models.CharField(max_length=255, blank=True, null=True, verbose_name="URL o ruta del botón")
    
    # Trazabilidad
    estado = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Relación con el administrador que creó/modificó el texto
    usuario_registro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='textos_registrados'
    )

    # Vinculamos el QuerySet
    objects = FonoApp_InfoGeneral_Queryset.as_manager()

    class Meta:
        db_table = 'FonoApp_InfoGeneral'
        verbose_name = 'Información General'
        verbose_name_plural = 'Información General'
        ordering = ['seccion', 'clave']

    def __str__(self):
        return f"{self.seccion} - {self.clave}"