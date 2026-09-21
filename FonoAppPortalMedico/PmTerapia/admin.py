from django.contrib import admin

from PmTerapia.models import PmEjercicio


@admin.register(PmEjercicio)
class PmEjercicioAdmin(admin.ModelAdmin):
    list_display = ('id_ejercicio', 'nombre', 'profesional', 'duracion_segundos', 'estado', 'fecha_creacion')
    list_filter = ('estado',)
    search_fields = ('nombre', 'profesional__nombres_profesional', 'profesional__apellidos_profesional')
