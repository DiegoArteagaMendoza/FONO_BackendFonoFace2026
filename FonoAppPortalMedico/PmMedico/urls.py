from django.urls import path
from PmMedico import views

urlpatterns = [
    # Aquí se irán registrando los endpoints del Portal Médico.
    # Formato de documentación usado en el resto del proyecto:
    #
    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/pm/medicos/listar/
    # HEADERS: Ninguno (Acceso público)
    # BODY: Ninguno
    # RESPUESTA ESPERADA: Arreglo JSON con los registros.
    # -------------------------------------------------------------------------
    # path('listar/', views.medicos_listar, name='medicos-listar'),
]
