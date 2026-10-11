from django.contrib import admin

from PmTerapia.models import PmEjercicio, PmPlanTerapia, PmPlanEjercicio, PmVideoProgreso


@admin.register(PmEjercicio)
class PmEjercicioAdmin(admin.ModelAdmin):
    list_display = ('id_ejercicio', 'nombre', 'profesional', 'duracion_segundos', 'estado', 'fecha_creacion')
    list_filter = ('estado',)
    search_fields = ('nombre', 'profesional__nombres_profesional', 'profesional__apellidos_profesional')


class PmPlanEjercicioInline(admin.TabularInline):
    model = PmPlanEjercicio
    extra = 0


@admin.register(PmPlanTerapia)
class PmPlanTerapiaAdmin(admin.ModelAdmin):
    list_display = ('id_plan', 'cliente', 'profesional', 'periodicidad', 'fecha_inicio', 'estado')
    list_filter = ('estado', 'periodicidad')
    inlines = [PmPlanEjercicioInline]


@admin.register(PmVideoProgreso)
class PmVideoProgresoAdmin(admin.ModelAdmin):
    list_display = ('id_video', 'plan_ejercicio', 'numero_periodo', 'fecha_subida', 'fecha_expiracion', 'estado')
    list_filter = ('estado', 'motivo_eliminacion')
