from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from Security.permissions import EsProfesional
from Security.archivos import guardar_o_400, borrar_de_cloudinary
from PmTerapia.models import PmEjercicio
from PmTerapia.serializer import PmEjercicioSerializer, PmEjercicioEditarSerializer


# ==========================================================================
# CATÁLOGO DE EJERCICIOS (lo administra el fonoaudiólogo)
# --------------------------------------------------------------------------
# Los ejercicios son privados de cada profesional. El dueño sale siempre del
# token, nunca del cuerpo, y toda consulta pasa por 'de_profesional': no hay
# forma de listar, editar ni borrar el ejercicio de otro. Cuando uno no es
# propio se responde 404, no 403, para no confirmar que existe.
# ==========================================================================

def _no_encontrado():
    return Response(
        {'error': 'El ejercicio no existe o no está en tu catálogo.'},
        status=status.HTTP_404_NOT_FOUND,
    )


@api_view(['GET'])
@permission_classes([EsProfesional])
def ejercicios_listar(request):
    """Catálogo vigente del fonoaudiólogo autenticado."""
    ejercicios = PmEjercicio.objects.de_profesional(request.user.pk)
    return Response(PmEjercicioSerializer(ejercicios, many=True).data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([EsProfesional])
@parser_classes([MultiPartParser, FormParser])
def ejercicio_crear(request):
    """
    Crea un ejercicio con su video de ejemplo (multipart/form-data).
    El video es obligatorio: un ejercicio sin demostración no le sirve al paciente.
    """
    serializer = PmEjercicioSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # El dueño sale del token, ignorando cualquier 'profesional' del body.
    error = guardar_o_400(serializer, profesional=request.user)
    if error:
        return error

    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@permission_classes([EsProfesional])
@parser_classes([MultiPartParser, FormParser])
def ejercicio_editar(request, id_ejercicio):
    """
    Edita nombre, instrucciones o el video de ejemplo.

    Si llega un video nuevo, el anterior se borra de Cloudinary DESPUÉS de que
    el nuevo quedó guardado: si la subida falla, el ejercicio conserva el que
    tenía en vez de quedarse sin ninguno.
    """
    ejercicio = PmEjercicio.objects.propio(id_ejercicio, request.user.pk)
    if not ejercicio:
        return _no_encontrado()

    video_anterior = ejercicio.video_ejemplo if 'video_ejemplo' in request.data else None

    serializer = PmEjercicioEditarSerializer(ejercicio, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    error = guardar_o_400(serializer)
    if error:
        return error

    if video_anterior:
        borrar_de_cloudinary(video_anterior)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([EsProfesional])
def ejercicio_eliminar(request, id_ejercicio):
    """
    Saca el ejercicio del catálogo (borrado lógico).

    Si algún plan de terapia lo tiene asignado, el video de ejemplo se conserva
    para que ese paciente lo siga viendo; si no, se borra de Cloudinary.
    """
    ejercicio = PmEjercicio.objects.propio(id_ejercicio, request.user.pk)
    if not ejercicio:
        return _no_encontrado()

    PmEjercicio.objects.eliminar(ejercicio)
    return Response({'mensaje': 'Ejercicio eliminado del catálogo'}, status=status.HTTP_200_OK)
