from django.db import models
from django.conf import settings
from FonoAppDiagnostico.queryset import (
    FonoApp_Diagnostico_Formulario_Queryset,
    FonoApp_Diagnostico_Respuesta_Queryset,
)


class FonoApp_Diagnostico_Formulario(models.Model):
    """Plantilla de un formulario/test clínico (ej. Índice de Fatiga Vocal, IDV-CH).

    Se registra de forma dinámica por el profesional autenticado -junto a sus
    subescalas y preguntas-, no existen tests precargados por fixture o migración.
    """
    id_formulario = models.AutoField("Código registro formulario", primary_key=True)

    nombre = models.CharField(max_length=150, verbose_name="Nombre del formulario")
    descripcion = models.TextField(blank=True, verbose_name="Instrucciones para el paciente")

    valor_minimo = models.PositiveSmallIntegerField(default=0, verbose_name="Valor mínimo de la escala")
    valor_maximo = models.PositiveSmallIntegerField(default=4, verbose_name="Valor máximo de la escala")

    estado = models.BooleanField(default=True, verbose_name="Activo")  # 1 = activo / 0 = desactivado
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")

    FonoApp_Administracion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='formularios_diagnostico_registrados',
        verbose_name='Registrado por',
    )

    objects = FonoApp_Diagnostico_Formulario_Queryset.as_manager()

    class Meta:
        db_table = 'FonoApp_Diagnostico_Formulario'
        managed = True
        verbose_name = "Formulario de diagnóstico"
        verbose_name_plural = "Formularios de diagnóstico"
        ordering = ['id_formulario']

    def __str__(self):
        return self.nombre


class FonoApp_Diagnostico_Subescala(models.Model):
    """Agrupa preguntas dentro de un formulario (ej. 'Parte 1', 'Funcional').

    El puntaje del test se descompone por subescala; un formulario sin
    subistinciones clínicas puede registrarse con una única subescala general.
    """
    id_subescala = models.AutoField("Código registro subescala", primary_key=True)

    formulario = models.ForeignKey(
        FonoApp_Diagnostico_Formulario, on_delete=models.CASCADE, related_name='subescalas'
    )
    nombre = models.CharField(max_length=100, verbose_name="Nombre de la subescala")
    orden = models.PositiveSmallIntegerField(default=0, verbose_name="Orden de despliegue")

    class Meta:
        db_table = 'FonoApp_Diagnostico_Subescala'
        managed = True
        verbose_name = "Subescala"
        verbose_name_plural = "Subescalas"
        ordering = ['formulario', 'orden']
        unique_together = [('formulario', 'orden')]

    def __str__(self):
        return f'{self.nombre} ({self.formulario.nombre})'


class FonoApp_Diagnostico_Pregunta(models.Model):
    id_pregunta = models.AutoField("Código registro pregunta", primary_key=True)

    formulario = models.ForeignKey(
        FonoApp_Diagnostico_Formulario, on_delete=models.CASCADE, related_name='preguntas'
    )
    subescala = models.ForeignKey(
        FonoApp_Diagnostico_Subescala, on_delete=models.CASCADE, related_name='preguntas'
    )
    texto = models.CharField(max_length=300, verbose_name="Enunciado de la pregunta")
    orden = models.PositiveSmallIntegerField(default=0, verbose_name="Orden de despliegue")

    class Meta:
        db_table = 'FonoApp_Diagnostico_Pregunta'
        managed = True
        verbose_name = "Pregunta"
        verbose_name_plural = "Preguntas"
        ordering = ['formulario', 'orden']

    def __str__(self):
        return f'{self.orden}. {self.texto[:50]}'


class FonoApp_Diagnostico_Interpretacion(models.Model):
    """Rango de puntaje asociado a un resultado clínico (ej. 0-10 'Leve', 11-20 'Moderado').

    Se define junto al formulario (o a una subescala) al momento de registrarlo, para que
    al calcular el resultado de una respuesta se pueda indicar no solo el puntaje sino
    también qué significa ese puntaje.

    Si 'subescala' es None, el rango interpreta el puntaje_total del test completo.
    Si tiene subescala, interpreta el puntaje de esa subescala en particular (ej. el
    IDV-CH interpreta por separado Funcional/Física/Emocional, no solo el total).
    """
    id_interpretacion = models.AutoField("Código registro interpretación", primary_key=True)

    formulario = models.ForeignKey(
        FonoApp_Diagnostico_Formulario, on_delete=models.CASCADE, related_name='interpretaciones'
    )
    subescala = models.ForeignKey(
        FonoApp_Diagnostico_Subescala, on_delete=models.CASCADE,
        related_name='interpretaciones', null=True, blank=True,
        verbose_name='Subescala (vacío = interpreta el puntaje total)',
    )

    valor_minimo = models.PositiveSmallIntegerField(verbose_name="Puntaje mínimo del rango")
    valor_maximo = models.PositiveSmallIntegerField(verbose_name="Puntaje máximo del rango")
    etiqueta = models.CharField(max_length=100, verbose_name="Resultado")
    descripcion = models.TextField(blank=True, verbose_name="Recomendación para el paciente")

    class Meta:
        db_table = 'FonoApp_Diagnostico_Interpretacion'
        managed = True
        verbose_name = "Interpretación de resultado"
        verbose_name_plural = "Interpretaciones de resultado"
        ordering = ['formulario', 'subescala', 'valor_minimo']

    def __str__(self):
        objetivo = self.subescala.nombre if self.subescala_id else 'Puntaje total'
        return f'{objetivo}: {self.valor_minimo}-{self.valor_maximo} = {self.etiqueta}'


class FonoApp_Diagnostico_Respuesta(models.Model):
    """Registro de una aplicación de un formulario a un paciente.

    FonoApp solo autentica cuentas profesionales (ver FonoAppAdministracion);
    el paciente no tiene cuenta propia, por lo que se identifica con datos libres.
    Por eso 'FonoApp_Administracion' es opcional: queda vacío cuando el propio
    cliente respondió desde el portal público, y registra al profesional solo
    cuando el test se aplicó desde una sesión autenticada.
    """
    id_respuesta = models.AutoField("Código registro resultado", primary_key=True)

    formulario = models.ForeignKey(
        FonoApp_Diagnostico_Formulario, on_delete=models.CASCADE, related_name='respuestas'
    )

    paciente_nombre = models.CharField(max_length=150, verbose_name="Nombre completo del paciente")
    paciente_fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de nacimiento")
    fecha_diligenciamiento = models.DateField(auto_now_add=True, verbose_name="Fecha de diligenciamiento")

    puntaje_total = models.PositiveIntegerField(default=0, verbose_name="Puntaje total")
    detalle_subescalas = models.JSONField(default=list, blank=True, verbose_name="Puntaje por subescala")
    interpretacion_total = models.JSONField(
        null=True, blank=True, verbose_name="Interpretación del puntaje total",
    )  # {'etiqueta': ..., 'descripcion': ...} según el rango de FonoApp_Diagnostico_Interpretacion
    # que contuvo a 'puntaje_total' al momento de registrar la respuesta. Queda None si el
    # formulario no tiene rangos definidos o si el puntaje no cayó en ninguno.

    FonoApp_Administracion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='diagnosticos_aplicados',
        verbose_name='Aplicado por',
        null=True,
        blank=True,
    )

    objects = FonoApp_Diagnostico_Respuesta_Queryset.as_manager()

    class Meta:
        db_table = 'FonoApp_Diagnostico_Respuesta'
        managed = True
        verbose_name = "Resultado de test"
        verbose_name_plural = "Resultados de test"
        ordering = ['-fecha_diligenciamiento', '-id_respuesta']

    def __str__(self):
        return f'{self.formulario.nombre} - {self.paciente_nombre}'


class FonoApp_Diagnostico_RespuestaDetalle(models.Model):
    respuesta = models.ForeignKey(
        FonoApp_Diagnostico_Respuesta, on_delete=models.CASCADE, related_name='detalles'
    )
    pregunta = models.ForeignKey(
        FonoApp_Diagnostico_Pregunta, on_delete=models.CASCADE, related_name='detalles'
    )
    valor = models.PositiveSmallIntegerField(verbose_name="Valor respondido")

    class Meta:
        db_table = 'FonoApp_Diagnostico_RespuestaDetalle'
        managed = True
        verbose_name = "Detalle de respuesta"
        verbose_name_plural = "Detalles de respuesta"
        unique_together = [('respuesta', 'pregunta')]

    def __str__(self):
        return f'Pregunta {self.pregunta_id} = {self.valor}'
