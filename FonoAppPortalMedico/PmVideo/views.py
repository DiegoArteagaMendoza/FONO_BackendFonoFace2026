from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from PmVideo.models import PmVideo
from PmVideo.serializer import PmVideoSerializer


# ==========================================================================
# SUBIDA DEL VIDEO (lo hace el cliente)
# --------------------------------------------------------------------------
# TODO: cuando el Portal Médico tenga su autenticación resuelta, este endpoint
# debe exigir sesión y tomar el cliente del token en vez de recibirlo en el
# cuerpo de la petición, para que nadie pueda subir videos a nombre de otro.
# ==========================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def video_subir(request):
    """
    Recibe el video de síntomas del cliente (multipart/form-data).
    La fecha de expiración se calcula sola: 30 días desde la subida.
    """
    serializer = PmVideoSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================================================
# CONSULTA Y ELIMINACIÓN (lado del profesional)
# --------------------------------------------------------------------------
# Exponen material clínico del paciente, por eso exigen autenticación.
# Hoy responden 403 hasta que se defina el login del Portal Médico.
# ==========================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def videos_listar(request):
    """
    Lista los videos vigentes. Se puede filtrar por cliente: ?cliente=1
    Los videos vencidos nunca se entregan, aunque el archivo aún no se haya purgado.
    """
    id_cliente = request.query_params.get('cliente', None)

    if id_cliente:
        videos = PmVideo.objects.del_cliente(id_cliente)
    else:
        videos = PmVideo.objects.vigentes()

    serializer = PmVideoSerializer(videos, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def video_detalle(request, id_video):
    """Retorna un video puntual, solo si sigue vigente."""
    video = PmVideo.objects.vigentes().filter(id_video=id_video).first()

    if not video:
        return Response(
            {'error': 'El video no existe, fue eliminado o ya cumplió sus 30 días'},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = PmVideoSerializer(video)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def video_eliminar(request, id_video):
    """
    Elimina el video por orden del médico: borra el archivo del disco y deja
    el registro marcado con el motivo para trazabilidad.
    """
    eliminado = PmVideo.objects.eliminar(id_video, PmVideo.MotivoEliminacion.ORDEN_MEDICA)

    if eliminado:
        return Response(
            {'mensaje': 'Video eliminado correctamente por orden médica'},
            status=status.HTTP_200_OK
        )

    return Response(
        {'error': 'El video no existe o ya estaba eliminado'},
        status=status.HTTP_404_NOT_FOUND
    )
