from django.db import migrations


class Migration(migrations.Migration):
    """Corrige el desfase entre el modelo y la tabla real en la BD compartida 'develop'.

    'FonoApp_Diagnostico_Respuesta.FonoApp_Administracion' se declaró null=True/blank=True
    en el modelo (ver 0001_initial) porque el cliente del portal responde el test sin
    sesión propia, pero la columna ya existía en MySQL como NOT NULL (la tabla se creó
    antes con una versión del modelo donde ese campo era obligatorio). Django no detecta
    este tipo de desfase porque compara contra el estado registrado de la migración, no
    contra la BD real -por eso se corrige con SQL explícito en vez de un AlterField, que
    hubiera sido un no-op al no cambiar el estado de la migración.

    Falla observada al responder el test como cliente anónimo (sin token):
        django.db.utils.IntegrityError: (1048, "Column 'FonoApp_Administracion_id'
        cannot be null")
    """

    dependencies = [
        ('FonoAppDiagnostico', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE `FonoApp_Diagnostico_Respuesta` "
                "MODIFY `FonoApp_Administracion_id` int(11) NULL"
            ),
            reverse_sql=(
                "ALTER TABLE `FonoApp_Diagnostico_Respuesta` "
                "MODIFY `FonoApp_Administracion_id` int(11) NOT NULL"
            ),
        ),
    ]
