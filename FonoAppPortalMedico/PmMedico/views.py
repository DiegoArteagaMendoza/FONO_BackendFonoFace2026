from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from PmMedico.models import (
    PM_Profesional, PM_Acreditacion, PM_Documento_Respaldo,
    PM_Especialidad, PM_Profesional_especialidad,
)
from PmMedico.serializer import (
    PM_ProfesionalRegistroSerializer, PM_ProfesionalSerializer, PM_ProfesionalDirectorioSerializer,
    PM_ProfesionalLoginSerializer, PM_ProfesionalCambiarPasswordSerializer,
    PM_AcreditacionSerializer, PM_ResolverAcreditacionSerializer,
    PM_Documento_RespaldoSerializer,
    PM_EspecialidadSerializer, PM_Profesional_especialidadSerializer,
)
from Security.permissions import EsAdministrador, EsProfesional, es_dueno_del_recurso


# =========================================================================
# PROFESIONAL: registro, sesión y perfil propio
# =========================================================================

@api_view(['POST'])
@permission_classes([AllowAny])  # Registro inicial ágil, sin autenticación previa
def profesional_registrar(request):
    """
    Crea el registro del fonoaudiólogo y abre automáticamente su acreditación
    en estado PENDIENTE. No exige documentos ni número de registro de salud
    en este paso (se piden después, ya autenticado).
    """
    serializer = PM_ProfesionalRegistroSerializer(data=request.data)
    if serializer.is_valid():
        profesional = serializer.save()
        return Response(PM_ProfesionalSerializer(profesional).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def profesional_login(request):
    """Autentica por email o RUT + contraseña y entrega un JWT propio del profesional."""
    credenciales = PM_ProfesionalLoginSerializer(data=request.data)
    credenciales.is_valid(raise_exception=True)

    profesional = PM_Profesional.objects.autenticar(
        credenciales.validated_data['identificador'],
        credenciales.validated_data['password'],
    )

    if not profesional:
        return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

    refresh = RefreshToken()
    refresh['id_profesional'] = profesional.pk
    access = refresh.access_token

    return Response({
        'refresh': str(refresh),
        'access': str(access),
        'profesional': {
            'id_profesional': profesional.pk,
            'nombres_profesional': profesional.nombres_profesional,
            'email_profesional': profesional.email_profesional,
        },
    })


@api_view(['GET'])
@permission_classes([EsProfesional])
def profesional_perfil(request):
    """Perfil completo del profesional autenticado (acreditación, documentos, especialidades)."""
    serializer = PM_ProfesionalSerializer(request.user)
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([EsProfesional])
def profesional_perfil_editar(request):
    """
    Edita datos de contacto/perfil propios. El RUT, la contraseña, el estado de
    la cuenta y el estado de verificación NO se pueden tocar desde aquí.
    """
    campos_editables = (
        'nombres_profesional', 'apellidos_profesional', 'email_profesional',
        'telefono_profesional', 'numero_registro_salud_profesional',
    )
    datos_a_actualizar = {campo: request.data[campo] for campo in campos_editables if campo in request.data}

    if not datos_a_actualizar:
        return Response({'error': 'Debe enviar al menos un campo editable'}, status=status.HTTP_400_BAD_REQUEST)

    # Reutilizamos el serializer para validar formato (email, teléfono, etc.) antes de persistir
    validador = PM_ProfesionalSerializer(request.user, data=datos_a_actualizar, partial=True)
    validador.is_valid(raise_exception=True)

    PM_Profesional.objects.editar_datos(request.user.pk, **datos_a_actualizar)

    request.user.refresh_from_db()
    return Response(PM_ProfesionalSerializer(request.user).data)


@api_view(['PUT'])
@permission_classes([EsProfesional])
def profesional_cambiar_password(request):
    """Cambia la contraseña propia; exige la contraseña actual para evitar el secuestro de sesión."""
    datos = PM_ProfesionalCambiarPasswordSerializer(data=request.data)
    datos.is_valid(raise_exception=True)

    exito, mensaje = PM_Profesional.objects.cambiar_password(
        request.user.pk,
        datos.validated_data['password_actual'],
        datos.validated_data['password_nueva'],
    )

    if exito:
        return Response({'mensaje': mensaje})
    return Response({'error': mensaje}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([EsProfesional])
def profesional_eliminar(request):
    """Baja lógica de la cuenta propia (no se borra físicamente el historial)."""
    PM_Profesional.objects.eliminar_logico(request.user.pk)
    return Response({'mensaje': 'Cuenta desactivada correctamente'})


# =========================================================================
# PROFESIONAL: consultas administrativas y directorio público
# =========================================================================

@api_view(['GET'])
@permission_classes([EsAdministrador])
def profesional_listar(request):
    """Listado administrativo, filtrable por ?estado_verificacion=PENDIENTE|EN_REVISION|APROBADO|RECHAZADO."""
    profesionales = PM_Profesional.objects.con_detalles().all()

    estado_verificacion = request.query_params.get('estado_verificacion')
    if estado_verificacion:
        profesionales = profesionales.filter(acreditaciones__estado_verificacion_profesional=estado_verificacion)

    serializer = PM_ProfesionalSerializer(profesionales.distinct(), many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([EsAdministrador])
def profesional_detalle(request, id_profesional):
    """Detalle administrativo completo de un profesional (para auditar su acreditación)."""
    try:
        profesional = PM_Profesional.objects.con_detalles().get(pk=id_profesional)
    except PM_Profesional.DoesNotExist:
        return Response({'error': 'Profesional no encontrado'}, status=status.HTTP_404_NOT_FOUND)

    return Response(PM_ProfesionalSerializer(profesional).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def profesional_directorio(request):
    """
    Directorio público: solo profesionales activos y con acreditación APROBADA,
    es decir, ya auditados y habilitados para prestar servicios.
    """
    profesionales = PM_Profesional.objects.verificados().prefetch_related('especialidades')
    serializer = PM_ProfesionalDirectorioSerializer(profesionales, many=True)
    return Response(serializer.data)


# =========================================================================
# DOCUMENTOS DE RESPALDO
# =========================================================================

@api_view(['POST'])
@permission_classes([EsProfesional])
def documento_subir(request):
    """
    Sube un documento probatorio propio (multipart/form-data):
      tipo_documeto_profesional: CEDULA_IDENTIDAD | CERTIFICADO_TITULO | CERTIFICADO_SUPERINTENDENCIA
      url_documento_profesional: archivo (PDF/JPG/PNG, máx. configurado en PM_MEDICO_DOCUMENTO_MAX_MB)
    """
    serializer = PM_Documento_RespaldoSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        documento = serializer.save()
        return Response(PM_Documento_RespaldoSerializer(documento).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([EsProfesional])
def documento_eliminar(request, id_documento):
    """Elimina un documento propio, solo si aún no fue validado por un administrador."""
    exito, mensaje = PM_Documento_Respaldo.objects.eliminar_si_no_validado(id_documento, request.user.pk)
    if exito:
        return Response({'mensaje': mensaje})
    return Response({'error': mensaje}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([EsAdministrador])
def profesional_documentos_listar(request, id_profesional):
    """Lista los documentos de un profesional para que el administrador los revise."""
    documentos = PM_Documento_Respaldo.objects.de_profesional(id_profesional)
    return Response(PM_Documento_RespaldoSerializer(documentos, many=True).data)


@api_view(['PATCH'])
@permission_classes([EsAdministrador])
def documento_validar(request, id_documento):
    """
    Marca (o desmarca) un documento como válido. Requiere el rol Admin (o
    SuperAdmin) de FonoApp; el resultado es el criterio que luego habilita
    aprobar la acreditación.
    """
    es_valido = request.data.get('documento_profesional_valido')
    if not isinstance(es_valido, bool):
        return Response(
            {'error': "Debe enviar 'documento_profesional_valido' como booleano (true/false)"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    actualizado = PM_Documento_Respaldo.objects.marcar_validez(id_documento, es_valido)
    if actualizado:
        return Response({'mensaje': 'Documento actualizado correctamente'})
    return Response({'error': 'Documento no encontrado'}, status=status.HTTP_404_NOT_FOUND)


# =========================================================================
# ACREDITACIÓN
# =========================================================================

@api_view(['GET'])
@permission_classes([EsAdministrador])
def acreditacion_pendientes(request):
    """Cola de solicitudes PENDIENTE/EN_REVISION que faltan por auditar."""
    acreditaciones = PM_Acreditacion.objects.pendientes()
    return Response(PM_AcreditacionSerializer(acreditaciones, many=True).data)


@api_view(['GET'])
@permission_classes([EsAdministrador | EsProfesional])
def acreditacion_estado(request, id_profesional):
    """Consulta el estado de acreditación vigente de un profesional (dueño o administrador)."""
    if isinstance(request.user, PM_Profesional) and not es_dueno_del_recurso(request.user, id_profesional):
        return Response({'error': 'No puede consultar la acreditación de otro profesional'}, status=status.HTTP_403_FORBIDDEN)

    acreditacion = PM_Acreditacion.objects.vigente_de(id_profesional)
    if not acreditacion:
        return Response({'error': 'El profesional no tiene solicitudes de acreditación'}, status=status.HTTP_404_NOT_FOUND)

    return Response(PM_AcreditacionSerializer(acreditacion).data)


@api_view(['PATCH'])
@permission_classes([EsAdministrador])
def acreditacion_resolver(request, id_acreditacion):
    """
    Aprueba o rechaza una acreditación. Requiere el rol Admin (o SuperAdmin)
    de FonoApp.
    Body: {"estado_verificacion_profesional": "APROBADO" | "RECHAZADO"}
    """
    entrada = PM_ResolverAcreditacionSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)

    acreditacion, error = PM_Acreditacion.objects.resolver(
        id_acreditacion,
        administrador=request.user,
        nuevo_estado=entrada.validated_data['estado_verificacion_profesional'],
    )

    if error:
        codigo = status.HTTP_404_NOT_FOUND if acreditacion is None and 'encontrada' in error else status.HTTP_400_BAD_REQUEST
        return Response({'error': error}, status=codigo)

    return Response(PM_AcreditacionSerializer(acreditacion).data)


# =========================================================================
# ESPECIALIDAD (catálogo administrado por Admin o SuperAdmin)
# =========================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def especialidad_listar(request):
    """Catálogo público de especialidades (se muestra en el formulario de registro/búsqueda)."""
    especialidades = PM_Especialidad.objects.all()
    return Response(PM_EspecialidadSerializer(especialidades, many=True).data)


@api_view(['POST'])
@permission_classes([EsAdministrador])
def especialidad_crear(request):
    serializer = PM_EspecialidadSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([EsAdministrador])
def especialidad_editar(request, id_especialidad):
    try:
        especialidad = PM_Especialidad.objects.get(pk=id_especialidad)
    except PM_Especialidad.DoesNotExist:
        return Response({'error': 'Especialidad no encontrada'}, status=status.HTTP_404_NOT_FOUND)

    serializer = PM_EspecialidadSerializer(especialidad, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([EsAdministrador])
def especialidad_eliminar(request, id_especialidad):
    filas_eliminadas, _detalle = PM_Especialidad.objects.filter(pk=id_especialidad).delete()
    if filas_eliminadas:
        return Response({'mensaje': 'Especialidad eliminada correctamente'})
    return Response({'error': 'Especialidad no encontrada'}, status=status.HTTP_404_NOT_FOUND)


# =========================================================================
# ESPECIALIDADES DEL PROFESIONAL (autogestión)
# =========================================================================

@api_view(['POST'])
@permission_classes([EsProfesional])
def profesional_especialidad_asignar(request):
    """Body: {"id_especialidad": <int>}. Exige certificado validado si la especialidad lo requiere."""
    serializer = PM_Profesional_especialidadSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        relacion = serializer.save()
        return Response(PM_Profesional_especialidadSerializer(relacion).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([EsProfesional])
def profesional_especialidad_quitar(request, id_especialidad):
    eliminado = PM_Profesional_especialidad.objects.quitar(request.user.pk, id_especialidad)
    if eliminado:
        return Response({'mensaje': 'Especialidad removida correctamente'})
    return Response({'error': 'El profesional no tiene asignada esa especialidad'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([AllowAny])
def profesional_especialidades_listar(request, id_profesional):
    """Especialidades públicas de un profesional ya verificado (para mostrarlas al buscar servicios)."""
    if not PM_Profesional.objects.verificados().filter(pk=id_profesional).exists():
        return Response({'error': 'Profesional no encontrado o aún no verificado'}, status=status.HTTP_404_NOT_FOUND)

    relaciones = PM_Profesional_especialidad.objects.de_profesional(id_profesional)
    return Response(PM_Profesional_especialidadSerializer(relaciones, many=True).data)
