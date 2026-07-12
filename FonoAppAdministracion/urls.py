from django.urls import path
from FonoAppAdministracion import views

urlpatterns = [
    # =========================================================================
    # RUTAS DE USUARIOS
    # =========================================================================

    # -------------------------------------------------------------------------
    # MÉTODO: POST
    # URL: /api/usuarios/crear/ (o el prefijo que uses)
    # HEADERS: Ninguno (acceso libre / AllowAny)
    # BODY (JSON): 
    # {
    #   "nombre": "Juan Pérez",
    #   "rut": "12345678-9",
    #   "email": "juan@ejemplo.com",
    #   "password": "mi_clave_secreta",
    #   "tipo": false,  # 0=vet, 1=indep
    #   "estado": true,
    #   "is_staff": false
    # }
    # -------------------------------------------------------------------------
    path('crear/', views.usuarios_create, name='usuarios-create'),

    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/usuarios/listar/
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY: Ninguno
    # USO: Retorna una lista JSON con todos los usuarios que tengan estado=True.
    # -------------------------------------------------------------------------
    path('listar/', views.usuarios_list, name='usuarios-list'),

    # -------------------------------------------------------------------------
    # MÉTODO: POST
    # URL: /api/usuarios/login/
    # HEADERS: Ninguno (acceso libre / AllowAny)
    # BODY (JSON): 
    # {
    #   "correo": "juan@ejemplo.com",
    #   "password": "mi_clave_secreta"
    # }
    # USO: Retorna los tokens JWT ('access' y 'refresh') y los datos básicos del usuario.
    # -------------------------------------------------------------------------
    path('login/', views.login_view, name='login'),

    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/usuarios/me/
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY: Ninguno
    # USO: Retorna todos los datos serializados del usuario dueño del token enviado.
    # -------------------------------------------------------------------------
    path('me/', views.usuario_perfil, name='usuario-perfil'),
    
    # -------------------------------------------------------------------------
    # MÉTODO: DELETE
    # URL: /api/usuarios/12345678-9/eliminar/
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY: Ninguno
    # USO: Desactiva a un usuario cambiando su estado a False (borrado lógico).
    # -------------------------------------------------------------------------
    path('<str:rut>/eliminar/', views.usuario_eliminar, name='usuario-eliminar'),

    # -------------------------------------------------------------------------
    # MÉTODO: PUT
    # URL: /api/usuarios/12345678-9/actualizar-password/
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY (JSON):
    # {
    #   "password": "mi_nueva_clave_secreta"
    # }
    # USO: Busca al usuario por su RUT y actualiza su contraseña de forma segura.
    # -------------------------------------------------------------------------
    path('<str:rut>/actualizar-password/', views.usuario_actualizar_password, name='usuario-actualizar-password'),


    # =========================================================================
    # RUTAS DE BANNERS DE INICIO
    # =========================================================================

    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/usuarios/banners/listar/ 
    # HEADERS: Ninguno (acceso libre / AllowAny)
    # BODY: Ninguno
    # RESPUESTA ESPERADA (JSON): 
    # [
    #   {
    #     "id_banner": 1,
    #     "titulo": "Bienvenidos al portal",
    #     "descripcion": "Texto descriptivo...",
    #     "fecha_creacion": "2026-06-26T10:00:00Z",
    #     "FonoApp_Administracion": 1,
    #     "imagenes": [
    #       { "id": 1, "imagen": "/media/banner/imagenes/foto.jpg" }
    #     ]
    #   }
    # ]
    # USO: Retorna un arreglo JSON con todos los banners activos y su respectiva imagen.
    # -------------------------------------------------------------------------
    path('banners/listar/', views.banner_listar, name='banner-listar'),

    # -------------------------------------------------------------------------
    # MÉTODO: POST
    # URL: /api/usuarios/banners/crear/
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY (FormData / multipart/form-data): 
    #   titulo: "Nuevo Banner"
    #   descripcion: "Descripción del banner..."
    #   imagenes_subidas: [Archivo de imagen] (Opcional, máximo 1 archivo)
    # USO: Crea un nuevo banner y asocia la imagen enviada validando el límite. 
    # RESPUESTA ESPERADA: El objeto JSON recién creado (Status 201).
    # -------------------------------------------------------------------------
    path('banners/crear/', views.banner_crear, name='banner-crear'),

    # -------------------------------------------------------------------------
    # MÉTODO: PUT o PATCH
    # URL: /api/usuarios/banners/1/editar/  <-- Reemplazar '1' por el id_banner
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY (JSON o FormData):
    # {
    #   "titulo": "Título editado",
    #   "descripcion": "Descripción actualizada..."
    # }
    # USO: Actualiza parcialmente los campos enviados de un banner existente.
    # RESPUESTA ESPERADA (JSON): { "mensaje": "Banner actualizado correctamente", "data": {...} }
    # -------------------------------------------------------------------------
    path('banners/<int:id_banner>/editar/', views.banner_editar, name='banner-editar'),

    # -------------------------------------------------------------------------
    # MÉTODO: DELETE
    # URL: /api/usuarios/banners/1/eliminar/ <-- Reemplazar '1' por el id_banner
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY: Ninguno
    # USO: Desactiva un banner cambiando su estado a False (borrado lógico).
    # RESPUESTA ESPERADA (JSON): { "mensaje": "Banner eliminado correctamente" }
    # -------------------------------------------------------------------------
    path('banners/<int:id_banner>/eliminar/', views.banner_eliminar, name='banner-eliminar'),
]