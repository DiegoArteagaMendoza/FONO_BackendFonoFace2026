"""
Agrega el código de seguimiento a PmCita.

En tres pasos y no en uno: el campo es único y obligatorio, pero ya hay citas
en la base. Añadirlo directamente exigiría un valor por defecto, y ese mismo
valor repetido en todas las filas rompería la restricción de unicidad. Así que
se añade opcional, se rellena fila por fila con un código distinto, y solo
entonces se marca como único y obligatorio.
"""

from django.db import migrations, models

from PmCita.models import generar_codigo_seguimiento


def _codigo_libre(usados):
    for _ in range(20):
        codigo = generar_codigo_seguimiento()
        if codigo not in usados:
            return codigo
    raise RuntimeError('No se pudo generar un código de seguimiento único.')


def asignar_codigos(apps, schema_editor):
    """Da un código único a cada cita que ya existía."""
    # El modelo histórico de la migración no trae los métodos de la clase real
    # (PmCita._codigo_unico no existe aquí), así que la unicidad se comprueba
    # contra el conjunto que se va llenando en esta misma pasada.
    PmCita = apps.get_model('PmCita', 'PmCita')

    usados = set(
        PmCita.objects.exclude(codigo_seguimiento=None)
        .values_list('codigo_seguimiento', flat=True)
    )

    for cita in PmCita.objects.filter(codigo_seguimiento=None):
        codigo = _codigo_libre(usados)
        cita.codigo_seguimiento = codigo
        cita.save(update_fields=['codigo_seguimiento'])
        usados.add(codigo)


def quitar_codigos(apps, schema_editor):
    """Marcha atrás: al volver al campo opcional no hace falta limpiar nada."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('PmCita', '0002_pmdisponibilidad'),
    ]

    operations = [
        migrations.AddField(
            model_name='pmcita',
            name='codigo_seguimiento',
            field=models.CharField(
                max_length=8, null=True, editable=False,
                verbose_name='Código de seguimiento',
            ),
        ),
        migrations.RunPython(asignar_codigos, quitar_codigos),
        migrations.AlterField(
            model_name='pmcita',
            name='codigo_seguimiento',
            field=models.CharField(
                max_length=8, unique=True, editable=False,
                verbose_name='Código de seguimiento',
            ),
        ),
    ]
