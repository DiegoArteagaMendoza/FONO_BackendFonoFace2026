from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from FonoAppDiagnostico.models import FonoApp_Diagnostico_Formulario, FonoApp_Diagnostico_Respuesta
from FonoAppDiagnostico.serializer import (
    FonoApp_Diagnostico_FormularioSerializer,
    FonoApp_Diagnostico_RespuestaSerializer,
    FonoApp_Diagnostico_RespuestaListadoSerializer,
    FonoApp_Diagnostico_EnviarCorreoSerializer,
)
from FonoAppDiagnostico.correos import enviar_resultado_diagnostico
from FonoAppFunciones.authentication import CustomJWTAuthentication


# =============================================================================
# FORMULARIOS (plantillas de test, ej. Índice de Fatiga Vocal / IDV-CH)
# =============================================================================

@api_view(['GET'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([AllowAny])
def formulario_listar(request):
    """Retorna todos los formularios activos junto a su estructura de subescalas y preguntas.

    Acceso público: el portal de cliente lista aquí las autoevaluaciones publicadas
    para que cualquier visitante pueda responderlas sin iniciar sesión.
    """
    formularios = FonoApp_Diagnostico_Formulario.objects.listar_todo()
    serializer = FonoApp_Diagnostico_FormularioSerializer(formularios, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([AllowAny])
def formulario_detalle(request, id_formulario):
    """Retorna un formulario activo con toda su estructura, lista para ser respondido.

    Acceso público: es la vista que el cliente carga para responder el test.
    """
    formulario = FonoApp_Diagnostico_Formulario.objects.obtener_activo(id_formulario)
    if not formulario:
        return Response({'error': 'Formulario no encontrado o inactivo'}, status=status.HTTP_404_NOT_FOUND)

    serializer = FonoApp_Diagnostico_FormularioSerializer(formulario)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def formulario_crear(request):
    """Registra un nuevo formulario junto a sus subescalas y preguntas.

    Este es el punto de entrada para que el profesional cree formularios como los
    de las imágenes de referencia (Índice de Fatiga Vocal, IDV-CH): no hay tests
    precargados, todos se dan de alta a través de este endpoint.
    """
    serializer = FonoApp_Diagnostico_FormularioSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def formulario_editar(request, id_formulario):
    """Edita campos simples del formulario (nombre, descripción, estado, rango de escala).

    No modifica subescalas ni preguntas ya registradas.
    """
    datos_a_actualizar = {}
    campos_validos = ['nombre', 'descripcion', 'estado', 'valor_minimo', 'valor_maximo']

    for campo in campos_validos:
        if campo in request.data:
            datos_a_actualizar[campo] = request.data[campo]

    if not datos_a_actualizar:
        return Response({'error': 'No se enviaron datos para actualizar'}, status=status.HTTP_400_BAD_REQUEST)

    actualizado = FonoApp_Diagnostico_Formulario.objects.editar_formulario(id_formulario, **datos_a_actualizar)
    if actualizado:
        return Response({'mensaje': 'Formulario actualizado correctamente'}, status=status.HTTP_200_OK)

    return Response({'error': 'Formulario no encontrado o inactivo'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def formulario_eliminar(request, id_formulario):
    """Ejecuta la baja lógica de un formulario, cambiando su estado a False."""
    actualizado = FonoApp_Diagnostico_Formulario.objects.eliminar_logico(id_formulario)
    if actualizado:
        return Response({'mensaje': 'Formulario eliminado correctamente'}, status=status.HTTP_200_OK)
    return Response({'error': 'Formulario no encontrado o ya eliminado'}, status=status.HTTP_404_NOT_FOUND)


# =============================================================================
# RESPUESTAS (aplicación del test a un paciente) y resultado calculado
# =============================================================================

@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([AllowAny])
def respuesta_crear(request):
    """Recibe la realización de un test (respuestas del paciente a cada pregunta)
    y entrega el resultado calculado: puntaje total y puntaje por subescala.

    Acceso público: el cliente del portal responde el test sin sesión propia
    ('FonoApp_Administracion' queda vacío en ese caso). Si la petición sí trae
    el token de un profesional/administrador autenticado, queda registrado como
    quien aplicó el test.
    """
    serializer = FonoApp_Diagnostico_RespuestaSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([AllowAny])
def respuesta_enviar_correo(request, id_respuesta):
    """Envía por correo el resultado ya calculado de una respuesta, al correo que
    el propio paciente escribe al terminar el test.

    Acceso público, igual que respuesta_crear: quien responde el test no tiene
    cuenta propia. El correo recibido NO se guarda en ningún modelo, solo se usa
    para este envío (ver FonoAppDiagnostico/correos.py); por eso la respuesta no
    devuelve más que si el envío se pudo hacer o no, igual que hace PmCita al
    confirmar una reserva.
    """
    entrada = FonoApp_Diagnostico_EnviarCorreoSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)

    respuesta = FonoApp_Diagnostico_Respuesta.objects.obtener_por_id(id_respuesta)
    if not respuesta:
        return Response({'error': 'Resultado no encontrado'}, status=status.HTTP_404_NOT_FOUND)

    correo_enviado = enviar_resultado_diagnostico(respuesta, entrada.validated_data['correo'])
    return Response({'correo_enviado': correo_enviado}, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def respuesta_listar_por_formulario(request, id_formulario):
    """Retorna los resultados ya registrados para un formulario específico."""
    respuestas = FonoApp_Diagnostico_Respuesta.objects.listar_por_formulario(id_formulario)
    serializer = FonoApp_Diagnostico_RespuestaListadoSerializer(respuestas, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
