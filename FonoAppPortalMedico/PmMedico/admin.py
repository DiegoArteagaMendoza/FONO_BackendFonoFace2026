from django.contrib import admin

from PmMedico.models import (
    PM_Profesional, PM_Acreditacion, PM_Documento_Respaldo,
    PM_Especialidad, PM_Profesional_especialidad,
)


class PM_Documento_RespaldoInline(admin.TabularInline):
    model = PM_Documento_Respaldo
    extra = 0
    readonly_fields = ('fecha_subida_documento_profesional',)


class PM_AcreditacionInline(admin.TabularInline):
    model = PM_Acreditacion
    extra = 0
    readonly_fields = ('fecha_solicitud_profesional',)


@admin.register(PM_Profesional)
class PM_ProfesionalAdmin(admin.ModelAdmin):
    list_display = (
        'id_profesional', 'nombres_profesional', 'apellidos_profesional',
        'rut_profesional', 'email_profesional', 'estado_cuenta_profesional',
    )
    list_filter = ('estado_cuenta_profesional',)
    search_fields = ('nombres_profesional', 'apellidos_profesional', 'rut_profesional', 'email_profesional')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion', 'password_profesional')
    inlines = [PM_AcreditacionInline, PM_Documento_RespaldoInline]


@admin.register(PM_Acreditacion)
class PM_AcreditacionAdmin(admin.ModelAdmin):
    list_display = (
        'id_acreditacion', 'id_profesional', 'estado_verificacion_profesional',
        'fecha_solicitud_profesional', 'fecha_resolucion_profesional', 'id_administrador_resolutor',
    )
    list_filter = ('estado_verificacion_profesional',)
    search_fields = ('id_profesional__nombres_profesional', 'id_profesional__apellidos_profesional')


@admin.register(PM_Documento_Respaldo)
class PM_Documento_RespaldoAdmin(admin.ModelAdmin):
    list_display = (
        'id_documento', 'id_profesional', 'tipo_documeto_profesional',
        'documento_profesional_valido', 'fecha_subida_documento_profesional',
    )
    list_filter = ('tipo_documeto_profesional', 'documento_profesional_valido')


@admin.register(PM_Especialidad)
class PM_EspecialidadAdmin(admin.ModelAdmin):
    list_display = ('id_especialidad', 'nombre_especialidad_profesional', 'especialidad_requiere_certificado')
    search_fields = ('nombre_especialidad_profesional',)


@admin.register(PM_Profesional_especialidad)
class PM_Profesional_especialidadAdmin(admin.ModelAdmin):
    list_display = ('id_profesional', 'id_especialidad', 'fecha_asignacion')
