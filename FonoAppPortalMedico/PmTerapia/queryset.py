from django.db import models


class PmEjercicio_Queryset(models.QuerySet):
    """
    Catálogo de ejercicios de un fonoaudiólogo.

    Todo pasa por 'de_profesional': los ejercicios son privados, y ninguna
    vista debería poder llegar a uno ajeno ni por accidente.
    """

    # ----------------------------------------------------------------
    # Consultas
    # ----------------------------------------------------------------

    def vigentes(self):
        """Los que siguen en el catálogo (no borrados)."""
        return self.filter(estado=True)

    def de_profesional(self, id_profesional):
        """Catálogo vigente de un fonoaudiólogo, del más nuevo al más antiguo."""
        return self.vigentes().filter(profesional_id=id_profesional).order_by('-fecha_creacion')

    def propio(self, id_ejercicio, id_profesional):
        """
        Un ejercicio vigente, solo si es de ese fonoaudiólogo. Devuelve None en
        cualquier otro caso: la vista responde 404 sin distinguir "no existe" de
        "no es tuyo", para no confirmar que existe.
        """
        return self.de_profesional(id_profesional).filter(id_ejercicio=id_ejercicio).first()

    # ----------------------------------------------------------------
    # Cambios
    # ----------------------------------------------------------------

    def eliminar(self, ejercicio):
        """
        Saca el ejercicio del catálogo.

        Es un borrado lógico: el registro queda por trazabilidad y porque los
        planes de terapia que lo tengan asignado deben seguir mostrándolo al
        paciente, con su video de ejemplo. El archivo solo se borra de
        Cloudinary si ningún plan lo referencia; mientras alguno lo use, se
        conserva.
        """
        ejercicio.estado = False
        ejercicio.save(update_fields=['estado', 'fecha_actualizacion'])

        if not ejercicio.esta_en_uso():
            ejercicio.eliminar_archivo_fisico()

        return ejercicio
