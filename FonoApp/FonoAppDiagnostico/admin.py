from django.contrib import admin
from FonoAppDiagnostico.models import (
    FonoApp_Diagnostico_Formulario,
    FonoApp_Diagnostico_Subescala,
    FonoApp_Diagnostico_Pregunta,
    FonoApp_Diagnostico_Interpretacion,
    FonoApp_Diagnostico_Respuesta,
    FonoApp_Diagnostico_RespuestaDetalle,
)


class PreguntaInline(admin.TabularInline):
    model = FonoApp_Diagnostico_Pregunta
    extra = 0


class InterpretacionInline(admin.TabularInline):
    model = FonoApp_Diagnostico_Interpretacion
    extra = 0
    fk_name = 'formulario'


class SubescalaInline(admin.TabularInline):
    model = FonoApp_Diagnostico_Subescala
    extra = 0


@admin.register(FonoApp_Diagnostico_Formulario)
class FonoApp_Diagnostico_FormularioAdmin(admin.ModelAdmin):
    list_display = ('id_formulario', 'nombre', 'valor_minimo', 'valor_maximo', 'estado', 'fecha_creacion')
    list_filter = ('estado',)
    search_fields = ('nombre',)
    inlines = [SubescalaInline, InterpretacionInline]


@admin.register(FonoApp_Diagnostico_Subescala)
class FonoApp_Diagnostico_SubescalaAdmin(admin.ModelAdmin):
    list_display = ('id_subescala', 'nombre', 'formulario', 'orden')
    list_filter = ('formulario',)
    inlines = [PreguntaInline]


@admin.register(FonoApp_Diagnostico_Interpretacion)
class FonoApp_Diagnostico_InterpretacionAdmin(admin.ModelAdmin):
    list_display = ('id_interpretacion', 'formulario', 'subescala', 'valor_minimo', 'valor_maximo', 'etiqueta')
    list_filter = ('formulario',)


@admin.register(FonoApp_Diagnostico_Pregunta)
class FonoApp_Diagnostico_PreguntaAdmin(admin.ModelAdmin):
    list_display = ('id_pregunta', 'texto', 'formulario', 'subescala', 'orden')
    list_filter = ('formulario',)


class RespuestaDetalleInline(admin.TabularInline):
    model = FonoApp_Diagnostico_RespuestaDetalle
    extra = 0


@admin.register(FonoApp_Diagnostico_Respuesta)
class FonoApp_Diagnostico_RespuestaAdmin(admin.ModelAdmin):
    list_display = (
        'id_respuesta', 'formulario', 'paciente_nombre', 'puntaje_total',
        'interpretacion_total', 'fecha_diligenciamiento',
    )
    list_filter = ('formulario',)
    search_fields = ('paciente_nombre',)
    inlines = [RespuestaDetalleInline]
